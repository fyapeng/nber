from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "data"
PAPERS_PATH = DATA_DIR / "papers.json"
ARCHIVE_PATH = DATA_DIR / "archive.json"
META_PATH = DATA_DIR / "update-meta.json"
CACHE_PATH = DATA_DIR / "translation-cache.json"

NBER_API_URL = "https://www.nber.org/api/v1/working_page_listing/contentType/working_paper/_/_/search"
NBER_ORIGIN = "https://www.nber.org"
SOURCE_URL = "https://www.nber.org/papers"
USER_AGENT = "fyapeng-nber-updater/1.0 (+https://github.com/fyapeng/nber)"

DATE_FIELDS = (
    "public_date",
    "date",
    "publication_date",
    "published_date",
    "publisheddate",
    "displaydate",
)

PUBLICATION_META_NAMES = (
    "citation_publication_date",
    "article:published_time",
    "DC.Date",
    "date",
)

ABSTRACT_SELECTORS = (
    "div.page-header__intro-inner",
    "div.page-header__intro",
    "section.abstract",
    "div.abstract",
    "div#abstract",
    "div.field--name-field-paper-abstract",
    ".paper-abstract",
    'meta[name="citation_abstract"]',
    'meta[property="og:description"]',
    'meta[name="description"]',
)

MAX_TRANSLATION_WORKERS = 2
TRANSLATION_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 5, 10)


@dataclass(frozen=True)
class DetailResult:
    abstract: str
    public_date: str | None
    notes: list[str]


@dataclass(frozen=True)
class TranslationResult:
    text: str
    status: str
    error: str | None
    cache_key: str | None = None
    cache_entry: dict[str, Any] | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp_path.replace(path)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    soup = BeautifulSoup(str(value), "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        try:
            return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        except (OSError, OverflowError, ValueError):
            return None

    text = clean_text(value)
    if not text:
        return None

    text = text.replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", " ", text)

    match = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            return None

    match = re.match(r"^(\d{4})[/-](\d{1,2})$", text)
    if match:
        year, month = (int(part) for part in match.groups())
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
        return None

    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    for fmt in ("%B %Y", "%b %Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            pass

    return None


def date_sort_key(date_text: str | None) -> tuple[int, int, int]:
    if not date_text:
        return (0, 0, 0)
    parts = [int(part) for part in date_text.split("-") if part.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def first_date_info(paper: dict[str, Any]) -> tuple[str | None, Any, str | None]:
    for field in DATE_FIELDS:
        raw_value = paper.get(field)
        normalized = normalize_date(raw_value)
        if normalized:
            return field, raw_value, normalized
    return None, None, None


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        }
    )
    return session


def fetch_listing(session: requests.Session, per_page: int) -> dict[str, Any]:
    params = {"page": 1, "perPage": per_page, "sortBy": "public_date"}
    logging.info("Fetching NBER listing API: %s", NBER_API_URL)
    try:
        response = session.get(NBER_API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"NBER listing request failed: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"NBER listing response is not valid JSON: {exc}") from exc


def extract_results(api_data: dict[str, Any]) -> list[dict[str, Any]]:
    results = api_data.get("results")
    if isinstance(results, list):
        return [paper for paper in results if isinstance(paper, dict)]
    raise RuntimeError("NBER API response did not contain a results list; refusing to overwrite data.")


def log_api_shape(api_data: dict[str, Any], papers: list[dict[str, Any]]) -> None:
    logging.info("NBER API top-level fields: %s", sorted(api_data.keys()))
    if not papers:
        logging.info("NBER API returned no papers in results.")
        return

    logging.info("First paper fields: %s", sorted(papers[0].keys()))
    for index, paper in enumerate(papers[:10], start=1):
        dates = {field: paper.get(field) for field in DATE_FIELDS if field in paper}
        logging.info(
            "Sample paper %s: url=%r newthisweek=%r dates=%s",
            index,
            paper.get("url"),
            paper.get("newthisweek"),
            dates,
        )


def select_candidate_batch(papers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, str | None]:
    if not papers:
        raise RuntimeError("NBER API returned an empty paper list; refusing to overwrite existing data.")

    new_this_week = [paper for paper in papers if paper.get("newthisweek") is True]
    if new_this_week:
        date_values = [first_date_info(paper)[2] for paper in new_this_week]
        batch_date = max((value for value in date_values if value), key=date_sort_key, default=None)
        logging.info("Selected %s papers by newthisweek == True.", len(new_this_week))
        return new_this_week, "newthisweek", batch_date

    date_groups: dict[str, list[dict[str, Any]]] = {}
    for paper in papers:
        _, _, normalized = first_date_info(paper)
        if normalized:
            date_groups.setdefault(normalized, []).append(paper)

    if not date_groups:
        raise RuntimeError(
            "No newthisweek papers and no recognizable date fields in the NBER listing; refusing to overwrite data."
        )

    latest_date = max(date_groups, key=date_sort_key)
    selected = date_groups[latest_date]
    logging.info(
        "newthisweek selected no papers; fell back to latest listing date batch %s with %s papers.",
        latest_date,
        len(selected),
    )
    return selected, "latest_listing_date", latest_date


def absolute_url(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return SOURCE_URL
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if not text.startswith("/"):
        text = "/" + text
    return f"{NBER_ORIGIN}{text}"


def paper_id_from_url(url: str, paper: dict[str, Any]) -> str:
    match = re.search(r"/papers/(w\d+)", url)
    if match:
        return match.group(1)
    for field in ("paper_id", "paperId", "nid", "id"):
        value = paper.get(field)
        if value:
            cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value)).strip("-")
            if cleaned:
                return cleaned[:80]
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"paper-{digest}"


def parse_authors(authors_value: Any) -> list[str]:
    authors: list[str] = []
    if isinstance(authors_value, list):
        items = authors_value
    elif authors_value:
        items = [authors_value]
    else:
        items = []

    for item in items:
        if isinstance(item, dict):
            name = clean_text(item.get("name") or item.get("title") or item.get("label"))
        else:
            name = clean_text(item)
        if name and name not in authors:
            authors.append(name)

    return authors or ["Unknown authors"]


def meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
    if not tag:
        return ""
    return str(tag.get("content") or "").strip()


def extract_abstract(soup: BeautifulSoup, paper_id: str) -> tuple[str, str | None]:
    primary_selector = ABSTRACT_SELECTORS[0]
    primary_node = soup.select_one(primary_selector)
    primary_found = primary_node is not None

    for selector in ABSTRACT_SELECTORS:
        node = soup.select_one(selector)
        if not node:
            continue

        if selector.startswith("meta"):
            text = str(node.get("content") or "").strip()
        else:
            text = node.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        if selector != primary_selector and not primary_found:
            logging.warning("Primary abstract selector missing for %s; used fallback selector %s.", paper_id, selector)
            return text, f"Primary abstract selector missing; used {selector}."
        return text, None

    return "", "No abstract selector matched the detail page."


def fetch_detail(session: requests.Session, paper_id: str, url: str) -> DetailResult:
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logging.warning("Detail request failed for %s: %s", paper_id, exc)
        return DetailResult("", None, [f"{paper_id}: detail request failed: {exc}"])

    soup = BeautifulSoup(response.text, "html.parser")

    public_date = None
    for name in PUBLICATION_META_NAMES:
        public_date = normalize_date(meta_content(soup, name))
        if public_date:
            break

    abstract, selector_note = extract_abstract(soup, paper_id)
    notes: list[str] = []
    if selector_note:
        notes.append(f"{paper_id}: {selector_note}")
    if not abstract:
        notes.append(f"{paper_id}: abstract not found; keeping an empty abstract.")

    return DetailResult(abstract, public_date, notes)


def build_records(
    session: requests.Session,
    candidates: list[dict[str, Any]],
    fetched_at: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    notes: list[str] = []

    for index, paper in enumerate(candidates, start=1):
        url = absolute_url(paper.get("url"))
        paper_id = paper_id_from_url(url, paper)
        title = clean_text(paper.get("title")) or paper_id
        authors = parse_authors(paper.get("authors"))
        _, _, list_date = first_date_info(paper)
        api_abstract = clean_text(paper.get("abstract"))

        logging.info("Fetching detail page %s/%s: %s", index, len(candidates), paper_id)
        detail = fetch_detail(session, paper_id, url)
        notes.extend(detail.notes)

        abstract = detail.abstract or api_abstract
        if not detail.abstract and api_abstract:
            notes.append(f"{paper_id}: used abstract text from the listing API.")

        records.append(
            {
                "id": paper_id,
                "title": title,
                "title_cn": title,
                "authors": authors,
                "abstract": abstract,
                "abstract_cn": abstract,
                "url": url,
                "public_date": detail.public_date or list_date,
                "translation_status": {
                    "title": "pending",
                    "abstract": "pending",
                },
                "translation_error": None,
                "fetched_at": fetched_at,
            }
        )

    return records, notes


def refine_to_latest_public_date(
    records: list[dict[str, Any]], selection_mode: str, initial_batch_date: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    date_groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        date_value = normalize_date(record.get("public_date"))
        if date_value:
            record["public_date"] = date_value
            date_groups.setdefault(date_value, []).append(record)

    if selection_mode == "newthisweek":
        batch_date = max(date_groups, key=date_sort_key, default=initial_batch_date)
        return records, batch_date

    if not date_groups:
        raise RuntimeError("Unable to identify publication dates after fetching detail pages; refusing to overwrite data.")

    latest_date = max(date_groups, key=date_sort_key)
    selected = date_groups[latest_date]
    if len(selected) != len(records):
        logging.info(
            "Refined fallback batch from %s candidates to %s papers with detail public_date %s.",
            len(records),
            len(selected),
            latest_date,
        )
    return selected, latest_date


def make_cache_key(paper_id: str, field: str, source_text: str) -> str:
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return f"{paper_id}:{field}:{digest}"


def seed_cache_from_existing(cache: dict[str, Any], existing_papers: list[dict[str, Any]]) -> int:
    seeded = 0
    for paper in existing_papers:
        paper_id = str(paper.get("id") or "")
        if not paper_id:
            continue
        status = paper.get("translation_status") or {}
        for field, translated_field in (("title", "title_cn"), ("abstract", "abstract_cn")):
            source = str(paper.get(field) or "")
            translated = str(paper.get(translated_field) or "")
            if not source or not translated or translated == source:
                continue
            if status.get(field) != "success":
                continue
            key = make_cache_key(paper_id, field, source)
            if key not in cache:
                cache[key] = {
                    "translation": translated,
                    "model": "seeded-from-existing-data",
                    "updated_at": utc_now_iso(),
                }
                seeded += 1
    return seeded


class TranslationService:
    def __init__(self, api_key: str | None, dry_run: bool, model: str) -> None:
        self.api_key = api_key
        self.dry_run = dry_run
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1") if api_key else None

    def translate(self, paper_id: str, field: str, source_text: str, cache: dict[str, Any]) -> TranslationResult:
        if not source_text:
            return TranslationResult("", "skipped_empty", None)

        key = make_cache_key(paper_id, field, source_text)
        cached = cache.get(key)
        if isinstance(cached, dict) and cached.get("translation"):
            return TranslationResult(str(cached["translation"]), "success", None, key)
        if isinstance(cached, str) and cached:
            return TranslationResult(cached, "success", None, key)

        if self.dry_run:
            return TranslationResult(source_text, "skipped_dry_run", None, key)

        if not self.client:
            return TranslationResult(source_text, "skipped_no_api_key", "KIMI_API_KEY is not set.", key)

        last_error = None
        for attempt in range(1, TRANSLATION_ATTEMPTS + 1):
            try:
                logging.info("Translating %s %s (attempt %s/%s).", paper_id, field, attempt, TRANSLATION_ATTEMPTS)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是专业的经济学论文翻译助手。请把英文内容准确、流畅地翻译为中文；"
                                "只输出译文，不要添加解释、标题或项目符号。"
                            ),
                        },
                        {"role": "user", "content": source_text},
                    ],
                    temperature=0.2,
                )
                translated = (response.choices[0].message.content or "").strip()
                if not translated:
                    raise RuntimeError("empty translation response")
                return TranslationResult(
                    translated,
                    "success",
                    None,
                    key,
                    {
                        "translation": translated,
                        "model": self.model,
                        "updated_at": utc_now_iso(),
                    },
                )
            except Exception as exc:  # noqa: BLE001 - API clients raise several exception families.
                last_error = str(exc)
                logging.warning("Kimi translation failed for %s %s: %s", paper_id, field, last_error)
                if attempt < TRANSLATION_ATTEMPTS:
                    time.sleep(BACKOFF_SECONDS[attempt - 1])

        return TranslationResult(source_text, "failed", last_error, key)


def translate_records(
    records: list[dict[str, Any]],
    cache: dict[str, Any],
    api_key: str | None,
    dry_run: bool,
    model: str,
    workers: int,
) -> dict[str, Any]:
    service = TranslationService(api_key=api_key, dry_run=dry_run, model=model)
    cache_updates: dict[str, dict[str, Any]] = {}
    worker_count = max(1, min(workers, MAX_TRANSLATION_WORKERS))

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map: dict[concurrent.futures.Future[TranslationResult], tuple[int, str, str]] = {}
        for index, record in enumerate(records):
            for field in ("title", "abstract"):
                source_text = str(record.get(field) or "")
                future = executor.submit(service.translate, record["id"], field, source_text, cache)
                future_map[future] = (index, field, source_text)

        for future in concurrent.futures.as_completed(future_map):
            index, field, source_text = future_map[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - keep one field failure from aborting the batch.
                result = TranslationResult(source_text, "failed", str(exc))
            record = records[index]
            record[f"{field}_cn"] = result.text
            record["translation_status"][field] = result.status

            errors = record.get("_translation_errors") or {}
            if result.error:
                errors[field] = result.error
            record["_translation_errors"] = errors

            if result.cache_key and result.cache_entry:
                cache_updates[result.cache_key] = result.cache_entry

    for record in records:
        errors = record.pop("_translation_errors", {})
        record["translation_error"] = errors or None

    return cache_updates


def build_meta(records: list[dict[str, Any]], batch_date: str, fetched_at: str, notes: list[str]) -> dict[str, Any]:
    failed_count = 0
    skipped_count = 0
    for record in records:
        statuses = record.get("translation_status") or {}
        for status in statuses.values():
            if status == "failed":
                failed_count += 1
            elif str(status).startswith("skipped"):
                skipped_count += 1

    clean_notes = list(dict.fromkeys(note for note in notes if note))
    if skipped_count:
        clean_notes.append(f"{skipped_count} translation fields were skipped.")

    return {
        "last_updated": fetched_at,
        "source": "NBER",
        "source_url": SOURCE_URL,
        "batch_date": batch_date,
        "paper_count": len(records),
        "failed_translations": failed_count,
        "notes": clean_notes,
    }


def update_archive(archive: Any, records: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(archive, list):
        archive = []
    batch_date = meta["batch_date"]
    retained = [entry for entry in archive if isinstance(entry, dict) and entry.get("batch_date") != batch_date]
    retained.insert(
        0,
        {
            "batch_date": batch_date,
            "last_updated": meta["last_updated"],
            "paper_count": len(records),
            "papers": records,
        },
    )
    return retained


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch NBER Working Papers and write Astro JSON data.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch papers and use cache only; do not call Kimi or write files.")
    parser.add_argument("--require-api-key", action="store_true", help="Exit with an error if KIMI_API_KEY is missing.")
    parser.add_argument("--per-page", type=int, default=50, help="Number of NBER listing results to fetch.")
    parser.add_argument("--model", default=os.environ.get("KIMI_MODEL", "moonshot-v1-8k"), help="Kimi model name.")
    parser.add_argument(
        "--translation-workers",
        type=int,
        default=MAX_TRANSLATION_WORKERS,
        help="Concurrent translation requests; capped at 2.",
    )
    return parser.parse_args()


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    api_key = os.environ.get("KIMI_API_KEY")

    if args.require_api_key and not api_key:
        logging.error("KIMI_API_KEY is required for this run but is not set.")
        return 2

    if args.dry_run:
        logging.info("Dry run enabled: Kimi API calls and file writes are disabled.")
    elif not api_key:
        logging.warning("KIMI_API_KEY is not set; translations will be marked skipped_no_api_key.")

    fetched_at = utc_now_iso()
    session = build_session()
    api_data = fetch_listing(session, args.per_page)
    papers = extract_results(api_data)
    log_api_shape(api_data, papers)

    candidates, selection_mode, initial_batch_date = select_candidate_batch(papers)
    records, notes = build_records(session, candidates, fetched_at)
    records, batch_date = refine_to_latest_public_date(records, selection_mode, initial_batch_date)

    if not records:
        raise RuntimeError("Selected paper batch is empty after detail processing; refusing to overwrite data.")
    if not batch_date:
        raise RuntimeError("Unable to determine a batch date; refusing to overwrite data.")

    cache = load_json(CACHE_PATH, {})
    if not isinstance(cache, dict):
        cache = {}
    existing_papers = load_json(PAPERS_PATH, [])
    if isinstance(existing_papers, list):
        seeded_count = seed_cache_from_existing(cache, existing_papers)
        if seeded_count:
            logging.info("Seeded %s successful translations from existing papers.json.", seeded_count)

    cache_updates = translate_records(records, cache, api_key, args.dry_run, args.model, args.translation_workers)
    cache.update(cache_updates)

    meta = build_meta(records, batch_date, fetched_at, notes)
    logging.info(
        "Prepared %s papers for batch %s; failed translation fields: %s.",
        meta["paper_count"],
        meta["batch_date"],
        meta["failed_translations"],
    )

    if args.dry_run:
        logging.info("Dry run complete. No files were written.")
        return 0

    archive = update_archive(load_json(ARCHIVE_PATH, []), records, meta)
    write_json(PAPERS_PATH, records)
    write_json(META_PATH, meta)
    write_json(CACHE_PATH, cache)
    write_json(ARCHIVE_PATH, archive)
    logging.info("Wrote %s, %s, %s, and %s.", PAPERS_PATH, META_PATH, CACHE_PATH, ARCHIVE_PATH)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:  # noqa: BLE001 - top-level CLI error reporting.
        logging.exception("Update failed: %s", exc)
        raise SystemExit(1)
