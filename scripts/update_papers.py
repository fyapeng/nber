from __future__ import annotations

import argparse
import concurrent.futures
import email
import hashlib
import html
import imaplib
import json
import logging
import os
import re
import ssl
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy, utils
from email.header import decode_header, make_header
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "data"
PAPERS_PATH = DATA_DIR / "papers.json"
ARCHIVE_PATH = DATA_DIR / "archive.json"
META_PATH = DATA_DIR / "update-meta.json"
CACHE_PATH = DATA_DIR / "translation-cache.json"
AUDIT_PATH = DATA_DIR / "translation-audit.md"
GLOSSARY_PATH = ROOT / "scripts" / "translation_glossary.json"
ENV_PATH = ROOT / ".env"

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

TITLE_META_NAMES = (
    "citation_title",
    "DC.Title",
    "og:title",
    "twitter:title",
)

AUTHOR_META_NAMES = (
    "citation_author",
    "DC.Creator",
    "author",
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
DETAIL_REQUEST_ATTEMPTS = 3
DETAIL_BACKOFF_SECONDS = (1, 3)
TRANSLATION_POLICY_VERSION = "2026-07-13-v2"


def load_translation_glossary(path: Path = GLOSSARY_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        glossary = json.load(handle)
    if not isinstance(glossary, dict):
        raise RuntimeError(f"Translation glossary must be a JSON object: {path}")
    return glossary


def glossary_fingerprint(glossary: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "policy_version": TRANSLATION_POLICY_VERSION,
            "version": glossary.get("version"),
            "prompt_terms": glossary.get("prompt_terms"),
            "replacement_rules": glossary.get("replacement_rules"),
            "global_cleanup": glossary.get("global_cleanup"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]


def build_translation_prompt(glossary: dict[str, Any]) -> str:
    def glossary_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    lines = [
        "你是给经济学研究者阅读 NBER Working Papers 的中文翻译助手。",
        "请使用中国大陆经济学学术写作中常见、准确、克制的译法。只输出译文，不要添加解释、标题、引号或项目符号。",
        "",
        "翻译原则：",
        "1. 优先准确传达经济学含义，不做软件、日常口语或新闻化误译。",
        "2. 论文标题译成简洁的学术标题；摘要译成自然的中文学术段落。",
        "3. 保留作者名、模型名、数据集名、缩写和必要专有名词。",
        "4. 不确定的专有概念宁可保留英文括注，也不要生造术语。",
        "5. 同一段内术语保持一致。",
        "6. 不要逐词硬译；长句可以按中文逻辑拆分，但不得省略限定条件、因果方向、比较对象或否定词。",
        "7. 原文中的数字、年份、百分比、货币单位、公式符号和缩写必须完整保留。",
        "8. 输出必须以中文为主；除必要专名和缩写外，不要整句照抄英文。",
        "",
        "术语约束：",
    ]
    for term in glossary.get("prompt_terms", []):
        if not isinstance(term, dict):
            continue
        source = glossary_text(term.get("source"))
        target = glossary_text(term.get("target"))
        note = glossary_text(term.get("note"))
        if not source or not target:
            continue
        line = f"- {source} -> {target}"
        if note:
            line = f"{line}；{note}"
        lines.append(line)
    return "\n".join(lines)


TRANSLATION_GLOSSARY = load_translation_glossary()
TRANSLATION_PROMPT_VERSION = f"{TRANSLATION_GLOSSARY.get('version', 'econ-zh')}-{glossary_fingerprint(TRANSLATION_GLOSSARY)}"
ECON_TRANSLATION_SYSTEM_PROMPT = build_translation_prompt(TRANSLATION_GLOSSARY)
IMAP_ENV_VARS = (
    "NBER_EMAIL_IMAP_HOST",
    "NBER_EMAIL_IMAP_PORT",
    "NBER_EMAIL_IMAP_USER",
    "NBER_EMAIL_IMAP_PASSWORD",
)
DEFAULT_EMAIL_LOOKBACK = 100
NEWSLETTER_SUBJECT = re.compile(r"^The Latest NBER Research\s*\((\d{4}-\d{2}-\d{2})\)$", re.IGNORECASE)
FORWARD_PREFIX = re.compile(r"^(?:fw|fwd|转发)\s*[:：]\s*", re.IGNORECASE)
CURATED_SUBJECT = re.compile(r"精选|值得读|推荐|arxiv|\b(?:curated|digest|picks|selection)\b", re.IGNORECASE)


class UnsafeBatchError(RuntimeError):
    """An identified source is unsafe; auto mode must not bypass it via fallback."""


@dataclass(frozen=True)
class DetailResult:
    title: str | None
    authors: list[str]
    abstract: str
    public_date: str | None
    notes: list[str]


@dataclass(frozen=True)
class EmailSourceResult:
    candidates: list[dict[str, Any]]
    batch_date: str | None
    message_id: str
    subject: str
    link_count: int


@dataclass(frozen=True)
class TranslationResult:
    text: str
    status: str
    error: str | None
    cache_key: str | None = None
    cache_entry: dict[str, Any] | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_local_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                logging.warning("Ignoring malformed .env line %s.", line_number)
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                logging.warning("Ignoring .env line %s with invalid variable name.", line_number)
                continue
            if key in os.environ:
                continue

            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value


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


def imap_config_from_env() -> tuple[str, int, str, str]:
    missing = [name for name in IMAP_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required IMAP environment variables: {', '.join(missing)}")

    host = os.environ["NBER_EMAIL_IMAP_HOST"].strip()
    user = os.environ["NBER_EMAIL_IMAP_USER"].strip()
    password = os.environ["NBER_EMAIL_IMAP_PASSWORD"]
    port_text = os.environ["NBER_EMAIL_IMAP_PORT"].strip()

    try:
        port = int(port_text)
    except ValueError as exc:
        raise RuntimeError("NBER_EMAIL_IMAP_PORT must be an integer.") from exc

    if not 1 <= port <= 65535:
        raise RuntimeError("NBER_EMAIL_IMAP_PORT must be between 1 and 65535.")
    if not host:
        raise RuntimeError("NBER_EMAIL_IMAP_HOST must not be empty.")
    if not user:
        raise RuntimeError("NBER_EMAIL_IMAP_USER must not be empty.")
    if not password:
        raise RuntimeError("NBER_EMAIL_IMAP_PASSWORD must not be empty.")

    return host, port, user, password


def has_imap_config() -> bool:
    return all(os.environ.get(name) for name in IMAP_ENV_VARS)


def positive_int_from_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        logging.warning("%s must be an integer; using %s.", name, default)
        return default
    return max(1, parsed)


def test_email_login() -> None:
    host, port, user, password = imap_config_from_env()
    context = ssl.create_default_context()
    mailbox: imaplib.IMAP4_SSL | None = None

    try:
        mailbox = imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=30)
        print(f"IMAP SSL connection successful: {host}:{port}")

        status, _ = mailbox.login(user, password)
        if status != "OK":
            raise RuntimeError(f"IMAP login returned status {status}.")
        print("IMAP login successful.")

        status, data = mailbox.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError(f"INBOX select returned status {status}.")
        count = data[0].decode("ascii", errors="replace") if data and data[0] else "0"
        print(f"INBOX message count: {count}")
    finally:
        if mailbox is not None:
            try:
                mailbox.logout()
            except imaplib.IMAP4.error:
                pass


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001 - keep malformed message headers from aborting a run.
        return value


def newsletter_edition(subject: str) -> str | None:
    subject = subject.strip()
    while FORWARD_PREFIX.match(subject):
        subject = FORWARD_PREFIX.sub("", subject, count=1).strip()
    match = NEWSLETTER_SUBJECT.fullmatch(subject)
    if not match:
        return None
    value = match.group(1)
    return value if normalize_date(value) == value else None


def batch_date_from_email(subjects: list[str], fallback_date_header: str | None = None) -> str | None:
    # Receipt/forwarding dates are deliberately irrelevant to edition identity.
    dates = {date for subject in subjects if (date := newsletter_edition(subject))}
    if len(dates) > 1:
        raise UnsafeBatchError("Conflicting newsletter editions; refusing to overwrite data.")
    return next(iter(dates), None)


def expand_encoded_text(value: str) -> str:
    current = value
    for _ in range(5):
        expanded = html.unescape(unquote(current))
        if expanded == current:
            break
        current = expanded
    return current


def part_text(part: email.message.Message) -> str:
    try:
        content = part.get_content()
        return content if isinstance(content, str) else str(content)
    except Exception:  # noqa: BLE001 - handle unusual charsets and malformed MIME parts.
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def nested_messages_from_part(part: email.message.Message) -> list[email.message.Message]:
    content_type = part.get_content_type()
    if content_type == "message/rfc822":
        payload = part.get_payload()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, email.message.Message)]

    payload_bytes = part.get_payload(decode=True)
    if not payload_bytes:
        return []

    filename = decode_mime_header(part.get_filename())
    looks_like_eml = filename.lower().endswith(".eml") or content_type in {
        "application/octet-stream",
        "message/rfc822",
    }
    if not looks_like_eml:
        return []
    if b"Subject:" not in payload_bytes[:10000] and b"Content-Type:" not in payload_bytes[:10000]:
        return []

    try:
        return [email.message_from_bytes(payload_bytes, policy=policy.default)]
    except Exception:  # noqa: BLE001 - ignore bad attachments and continue with visible body text.
        return []


def message_parts(message: email.message.Message):
    """Walk this message's MIME parts without leaking attached messages into its body."""
    if message.get_content_type() == "message/rfc822":
        yield message
    elif message.is_multipart():
        for part in message.get_payload():
            yield from message_parts(part)
    else:
        yield message


def newsletter_from_message(message: email.message.Message) -> list[EmailSourceResult]:
    subject = decode_mime_header(message.get("Subject"))
    if CURATED_SUBJECT.search(subject):
        return []
    # Optional explicit allowlist, checked against the outer envelope for forwards.
    # No default sender is guessed: production headers are not available in this repo.
    allowed = {value.strip().casefold() for value in os.environ.get("NBER_EMAIL_ALLOWED_SENDERS", "").split(",") if value.strip()}
    sender = utils.parseaddr(str(message.get("From") or ""))[1].casefold()
    if allowed and sender not in allowed:
        return []
    return newsletter_payloads(message)


def newsletter_payloads(message: email.message.Message) -> list[EmailSourceResult]:
    subject = decode_mime_header(message.get("Subject"))
    if CURATED_SUBJECT.search(subject):
        return []
    parts = list(message_parts(message))
    nested = [nested for part in parts for nested in nested_messages_from_part(part)]
    if nested:
        # An .eml forward contributes only the original message, never wrapper links.
        results = [result for child in nested for result in newsletter_payloads(child)]
        if results:
            outer_date = newsletter_edition(subject)
            if outer_date and any(result.batch_date != outer_date for result in results):
                raise UnsafeBatchError("Forward subject and attached newsletter edition disagree.")
            return results

    edition = newsletter_edition(subject)
    texts = []
    inline_editions = []
    for part in parts:
        if part.get_content_type() not in {"text/plain", "text/html"} or part.get_content_disposition() == "attachment":
            continue
        text = part_text(part)
        if part.get_content_type() == "text/html":
            # Preserve hrefs for tracking URL extraction as well as visible headers.
            soup = BeautifulSoup(text, "html.parser")
            for anchor in soup.find_all("a", href=True):
                anchor.append(" " + str(anchor["href"]))
            text = soup.get_text("\n", strip=True)
        # Common plain/HTML inline-forward headers, with optional quote prefixes.
        text = re.sub(r"(?m)^\s*>+\s?", "", text)
        headers = list(re.finditer(r"(?im)^(?:Subject|主题)\s*[:：]\s*(The Latest NBER Research\s*\(\d{4}-\d{2}-\d{2}\))\s*$", text))
        if headers:
            inline_editions.extend(match.group(1) for match in headers)
            text = text[headers[0].end():]
        texts.append((bool(headers), text))
    inline_date = batch_date_from_email(inline_editions)
    if edition and inline_date and edition != inline_date:
        raise UnsafeBatchError("Forward subject and original newsletter edition disagree.")
    # A generic wrapper is accepted only when it is explicitly a forward and has
    # an original Subject header. Arbitrary research/curated emails cannot qualify.
    if edition is None and FORWARD_PREFIX.match(subject):
        edition = inline_date
    if edition is None:
        return []
    # Once an original Subject identifies an inline forward, headerless MIME
    # companions are wrappers, not evidence of original newsletter membership.
    original_texts = [text for has_header, text in texts if has_header or not inline_editions]
    links = extract_paper_links_from_text("\n".join(original_texts))
    # Keep dated empty candidates until selection: a newer empty newsletter must
    # stop the update, but an older empty copy must not block a valid newer issue.
    return [EmailSourceResult(
        candidates=[{"url": link, "source": "email"} for link in links],
        batch_date=edition,
        message_id="",
        subject=f"The Latest NBER Research ({edition})",
        link_count=len(links),
    )]


def select_email_edition(results: list[EmailSourceResult]) -> EmailSourceResult:
    if not results:
        raise RuntimeError("No recognized NBER newsletter with a dated official subject found.")
    newest = max(str(result.batch_date) for result in results)
    same_edition = [result for result in results if result.batch_date == newest]
    for result in results:
        if not result.candidates:
            if result.batch_date == newest:
                raise UnsafeBatchError(f"Newsletter edition {newest} has an empty copy; cannot confirm complete membership.")
            logging.warning("Ignoring empty older newsletter edition %s while selecting edition %s.", result.batch_date, newest)
    # Prefer a complete resend/forward even if a shorter copy arrived later.
    selected = max(same_edition, key=lambda result: result.link_count)
    selected_ids = candidate_ids(selected.candidates)
    for result in same_edition:
        if not candidate_ids(result.candidates) <= selected_ids:
            raise UnsafeBatchError(f"Conflicting paper IDs in emails for edition {newest}.")
    logging.info("Selected newsletter edition %s with %s paper links.", newest, selected.link_count)
    return selected


def extract_paper_links_from_text(text: str) -> list[str]:
    expanded = expand_encoded_text(text)
    candidates: list[str] = []
    candidates.extend(re.findall(r"https?://[^\s<>'\")]+", expanded, flags=re.IGNORECASE))
    candidates.extend(re.findall(r"href=[\"']([^\"']+)[\"']", expanded, flags=re.IGNORECASE))

    links: list[str] = []
    index = 0
    seen: set[str] = set()
    while index < len(candidates):
        raw = expand_encoded_text(candidates[index]).rstrip(".,;])}")
        index += 1
        if raw in seen:
            continue
        seen.add(raw)

        parsed = urlparse(raw)
        for values in parse_qs(parsed.query).values():
            for value in values:
                if "nber" in value.lower() or "/papers/" in value.lower():
                    candidates.append(value)

        match = re.fullmatch(r"/papers/(w\d+)/?", parsed.path, flags=re.IGNORECASE)
        if match and (parsed.hostname in {"nber.org", "www.nber.org"} or (not parsed.netloc and raw.startswith("/papers/"))):
            url = f"{NBER_ORIGIN}/papers/{match.group(1).lower()}"
            if url not in links:
                links.append(url)

    return links


def fetch_email_candidates(lookback: int = DEFAULT_EMAIL_LOOKBACK) -> EmailSourceResult:
    host, port, user, password = imap_config_from_env()
    mailbox_name = os.environ.get("NBER_EMAIL_IMAP_MAILBOX", "INBOX")
    context = ssl.create_default_context()
    mailbox: imaplib.IMAP4_SSL | None = None

    try:
        mailbox = imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=30)
        status, _ = mailbox.login(user, password)
        if status != "OK":
            raise RuntimeError(f"IMAP login returned status {status}.")

        status, _ = mailbox.select(mailbox_name, readonly=True)
        if status != "OK":
            raise RuntimeError(f"IMAP mailbox select returned status {status}.")

        status, ids_data = mailbox.search(None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search returned status {status}.")
        message_ids = ids_data[0].split() if ids_data and ids_data[0] else []

        results: list[EmailSourceResult] = []
        for message_id in reversed(message_ids[-lookback:]):
            # Fetch read-only bodies too: generic .eml forwards need not mention NBER
            # in the outer subject. The scan remains bounded by email-lookback.
            status, full_data = mailbox.fetch(message_id, "(BODY.PEEK[])")
            if status != "OK":
                raise UnsafeBatchError("Could not read all candidate emails; refusing a partial mailbox scan.")
            raw_message = b"".join(part[1] for part in full_data if isinstance(part, tuple) and part[1])
            if not raw_message:
                raise UnsafeBatchError("Empty IMAP response; refusing a partial mailbox scan.")
            message = email.message_from_bytes(raw_message, policy=policy.default)
            results.extend(newsletter_from_message(message))
        return select_email_edition(results)

    finally:
        if mailbox is not None:
            try:
                mailbox.logout()
            except imaplib.IMAP4.error:
                pass


def fetch_api_candidates() -> tuple[list[dict[str, Any]], str, str | None]:
    # The listing provides paper publication dates/newthisweek, not a newsletter
    # edition or an authoritative membership manifest. Page 1 (50 rows) can also
    # truncate a week. Fail closed rather than invent an edition from max(date).
    raise UnsafeBatchError(
        "NBER API listing cannot establish newsletter edition or complete membership; "
        "refusing API fallback before translation or writes. Use a dated official newsletter."
    )


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


def meta_contents(soup: BeautifulSoup, name: str) -> list[str]:
    values: list[str] = []
    for attrs in ({"name": name}, {"property": name}):
        for tag in soup.find_all("meta", attrs=attrs):
            text = str(tag.get("content") or "").strip()
            if text and text not in values:
                values.append(text)
    return values


def extract_detail_title(soup: BeautifulSoup) -> str | None:
    for name in TITLE_META_NAMES:
        title = clean_text(meta_content(soup, name))
        if title:
            return re.sub(r"\s*\|\s*NBER.*$", "", title, flags=re.IGNORECASE).strip()

    for selector in ("h1.page-header__title", "h1"):
        node = soup.select_one(selector)
        if node:
            title = clean_text(node.get_text(" ", strip=True))
            if title:
                return title
    return None


def extract_detail_authors(soup: BeautifulSoup) -> list[str]:
    authors: list[str] = []
    for name in AUTHOR_META_NAMES:
        for value in meta_contents(soup, name):
            author = clean_text(value)
            if author and author not in authors:
                authors.append(author)

    if authors:
        return authors

    for selector in (
        ".page-header__authors a",
        ".page-header__authors",
        ".field--name-field-paper-authors a",
        ".field--name-field-paper-authors",
    ):
        for node in soup.select(selector):
            author = clean_text(node.get_text(" ", strip=True))
            if author and author not in authors:
                authors.append(author)
        if authors:
            return authors

    return []


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
    last_error: requests.RequestException | None = None
    response: requests.Response | None = None
    for attempt in range(1, DETAIL_REQUEST_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            last_error = None
            break
        except requests.RequestException as exc:
            last_error = exc
            logging.warning(
                "Detail request failed for %s (attempt %s/%s): %s",
                paper_id,
                attempt,
                DETAIL_REQUEST_ATTEMPTS,
                exc,
            )
            if attempt < DETAIL_REQUEST_ATTEMPTS:
                time.sleep(DETAIL_BACKOFF_SECONDS[attempt - 1])

    if response is None or last_error is not None:
        error = last_error or RuntimeError("detail request returned no response")
        return DetailResult(None, [], "", None, [f"{paper_id}: detail request failed after retries: {error}"])

    soup = BeautifulSoup(response.text, "html.parser")
    title = extract_detail_title(soup)
    authors = extract_detail_authors(soup)

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

    return DetailResult(title, authors, abstract, public_date, notes)


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
        api_title = clean_text(paper.get("title"))
        authors = parse_authors(paper.get("authors"))
        _, _, list_date = first_date_info(paper)
        api_abstract = clean_text(paper.get("abstract"))

        logging.info("Fetching detail page %s/%s: %s", index, len(candidates), paper_id)
        detail = fetch_detail(session, paper_id, url)
        notes.extend(detail.notes)

        title = api_title or detail.title or paper_id
        if not api_title and detail.title:
            notes.append(f"{paper_id}: used title from the detail page.")
        if authors == ["Unknown authors"] and detail.authors:
            authors = detail.authors
            notes.append(f"{paper_id}: used authors from the detail page.")

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
                "translation_prompt_version": TRANSLATION_PROMPT_VERSION,
                "fetched_at": fetched_at,
            }
        )

    return records, notes


def refine_to_latest_public_date(
    records: list[dict[str, Any]], selection_mode: str, initial_batch_date: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    if selection_mode != "email" or not initial_batch_date:
        raise UnsafeBatchError("A dated newsletter edition is required; publication dates are not batch dates.")
    for record in records:
        normalized = normalize_date(record.get("public_date"))
        if normalized:
            record["public_date"] = normalized
    return records, initial_batch_date


def make_cache_key(paper_id: str, field: str, source_text: str) -> str:
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return f"{TRANSLATION_PROMPT_VERSION}:{paper_id}:{field}:{digest}"


def translation_quality_issue(source_text: str, translated: str, field: str) -> str | None:
    source = re.sub(r"\s+", " ", source_text).strip()
    target = re.sub(r"\s+", " ", translated).strip()
    if not target:
        return "empty translation"
    if source.casefold() == target.casefold():
        return "translation is identical to the English source"

    source_letters = len(re.findall(r"[A-Za-z]", source))
    chinese_chars = len(re.findall(r"[\u3400-\u9fff]", target))
    if source_letters >= 12 and chinese_chars == 0:
        return "translation contains no Chinese text"
    if field == "abstract" and len(source) >= 240 and chinese_chars < 20:
        return "abstract translation contains too little Chinese text"
    if field == "abstract" and len(source) >= 240 and len(target) < len(source) * 0.12:
        return "abstract translation is implausibly short"
    return None


def apply_translation_rules(source_text: str, translated: str) -> str:
    text = translated.strip()
    text = re.sub(r"^(?:译文|中文翻译|翻译)\s*[：:]\s*", "", text, count=1)
    source_lower = source_text.lower()
    source_exact = source_text.strip().lower()

    def safe_replace(value: str, old: str, new: str) -> str:
        if not old or old not in value:
            return value
        if old not in new or new not in value:
            return value.replace(old, new)

        # Protect already-correct occurrences when the preferred wording contains
        # the text it replaces (for example, 提取失败 -> 记忆提取失败).
        placeholder = "\u0000NBER_TRANSLATION_RULE\u0000"
        while placeholder in value:
            placeholder += "_"
        protected = value.replace(new, placeholder)
        return protected.replace(old, new).replace(placeholder, new)

    def rule_matches(rule: dict[str, Any]) -> bool:
        exact = str(rule.get("source_exact") or "").strip().lower()
        if exact and exact != source_exact:
            return False

        contains = str(rule.get("source_contains") or "").strip().lower()
        if contains and contains not in source_lower:
            return False

        contains_all = rule.get("source_contains_all") or []
        if isinstance(contains_all, list):
            for item in contains_all:
                needle = str(item).strip().lower()
                if needle and needle not in source_lower:
                    return False

        contains_any = rule.get("source_contains_any") or []
        if isinstance(contains_any, list) and contains_any:
            needles = [str(item).strip().lower() for item in contains_any if str(item).strip()]
            if needles and not any(needle in source_lower for needle in needles):
                return False

        return bool(exact or contains or contains_all or contains_any)

    for rule in TRANSLATION_GLOSSARY.get("replacement_rules", []):
        if not isinstance(rule, dict) or not rule_matches(rule):
            continue
        override = rule.get("override")
        if isinstance(override, str) and override.strip():
            text = override.strip()
            continue
        replacements = rule.get("replacements") or []
        if not isinstance(replacements, list):
            continue
        for replacement in replacements:
            if not isinstance(replacement, dict):
                continue
            old = str(replacement.get("bad") or "")
            new = str(replacement.get("good") or "")
            if old:
                text = safe_replace(text, old, new)

    for replacement in TRANSLATION_GLOSSARY.get("global_cleanup", []):
        if not isinstance(replacement, dict):
            continue
        old = str(replacement.get("bad") or "")
        new = str(replacement.get("good") or "")
        if old:
            text = safe_replace(text, old, new)

    return text


def seed_cache_from_existing(cache: dict[str, Any], existing_papers: list[dict[str, Any]]) -> int:
    seeded = 0
    for paper in existing_papers:
        paper_id = str(paper.get("id") or "")
        if not paper_id:
            continue
        if paper.get("translation_prompt_version") != TRANSLATION_PROMPT_VERSION:
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
                    "prompt_version": TRANSLATION_PROMPT_VERSION,
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
            cached_text = str(cached["translation"])
            translated = apply_translation_rules(source_text, cached_text)
            issue = translation_quality_issue(source_text, translated, field)
            if not issue:
                cache_entry = None
                if translated != cached_text:
                    cache_entry = {
                        **cached,
                        "translation": translated,
                        "prompt_version": TRANSLATION_PROMPT_VERSION,
                        "updated_at": utc_now_iso(),
                    }
                return TranslationResult(translated, "success", None, key, cache_entry)
            logging.warning("Ignoring invalid cached translation for %s %s: %s", paper_id, field, issue)
        if isinstance(cached, str) and cached:
            translated = apply_translation_rules(source_text, cached)
            issue = translation_quality_issue(source_text, translated, field)
            if not issue:
                cache_entry = None
                if translated != cached:
                    cache_entry = {
                        "translation": translated,
                        "model": "normalized-from-cache",
                        "prompt_version": TRANSLATION_PROMPT_VERSION,
                        "updated_at": utc_now_iso(),
                    }
                return TranslationResult(translated, "success", None, key, cache_entry)
            logging.warning("Ignoring invalid legacy cache for %s %s: %s", paper_id, field, issue)

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
                            "content": ECON_TRANSLATION_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": f"请翻译以下 NBER 论文{'标题' if field == 'title' else '摘要'}：\n\n{source_text}",
                        },
                    ],
                    temperature=0.1,
                )
                translated = apply_translation_rules(source_text, response.choices[0].message.content or "")
                issue = translation_quality_issue(source_text, translated, field)
                if issue:
                    raise RuntimeError(f"translation quality check failed: {issue}")
                return TranslationResult(
                    translated,
                    "success",
                    None,
                    key,
                    {
                        "translation": translated,
                        "model": self.model,
                        "prompt_version": TRANSLATION_PROMPT_VERSION,
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


def table_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "\\|").strip()


def clipped(value: str, needle: str = "", radius: int = 54) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if not needle:
        return text[: radius * 2]
    index = text.find(needle)
    if index < 0:
        return text[: radius * 2]
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def build_translation_audit_report(records: list[dict[str, Any]], glossary: dict[str, Any], generated_at: str) -> str:
    audit_config = glossary.get("audit") if isinstance(glossary.get("audit"), dict) else {}
    suspect_terms = audit_config.get("suspect_translations") if isinstance(audit_config, dict) else []
    source_terms = audit_config.get("source_terms") if isinstance(audit_config, dict) else []
    allowed_english_terms = {
        str(term).lower()
        for term in (audit_config.get("allowed_english_terms") if isinstance(audit_config, dict) else []) or []
    }

    suspect_hits: list[dict[str, str]] = []
    for suspect in suspect_terms if isinstance(suspect_terms, list) else []:
        if not isinstance(suspect, dict):
            continue
        bad = str(suspect.get("bad") or "")
        if not bad:
            continue
        for record in records:
            for field in ("title_cn", "abstract_cn"):
                value = str(record.get(field) or "")
                if bad in value:
                    suspect_hits.append(
                        {
                            "id": str(record.get("id") or ""),
                            "field": field,
                            "bad": bad,
                            "suggestion": str(suspect.get("suggestion") or ""),
                            "reason": str(suspect.get("reason") or ""),
                            "context": clipped(value, bad),
                        }
                    )

    missing_preferred: list[dict[str, str]] = []
    for source_term in source_terms if isinstance(source_terms, list) else []:
        if not isinstance(source_term, dict):
            continue
        term = str(source_term.get("term") or "").strip()
        preferred = str(source_term.get("preferred") or "").strip()
        if not term or not preferred:
            continue
        term_lower = term.lower()
        for record in records:
            english = f"{record.get('title') or ''}\n{record.get('abstract') or ''}".lower()
            chinese = f"{record.get('title_cn') or ''}\n{record.get('abstract_cn') or ''}"
            if term_lower in english and preferred not in chinese:
                missing_preferred.append(
                    {
                        "id": str(record.get("id") or ""),
                        "term": term,
                        "preferred": preferred,
                        "title": str(record.get("title") or ""),
                        "title_cn": str(record.get("title_cn") or ""),
                    }
                )

    failed_fields: list[dict[str, str]] = []
    quality_hits: list[dict[str, str]] = []
    for record in records:
        statuses = record.get("translation_status") if isinstance(record.get("translation_status"), dict) else {}
        errors = record.get("translation_error") if isinstance(record.get("translation_error"), dict) else {}
        for field in ("title", "abstract"):
            status = str(statuses.get(field) or "")
            if status == "failed" or status.startswith("skipped"):
                error_value = errors.get(field, "") if isinstance(errors, dict) else ""
                failed_fields.append(
                    {
                        "id": str(record.get("id") or ""),
                        "field": field,
                        "status": status,
                        "error": str(error_value or ""),
                    }
                )
            source_text = str(record.get(field) or "")
            translated_text = str(record.get(f"{field}_cn") or "")
            issue = translation_quality_issue(source_text, translated_text, field)
            if issue:
                quality_hits.append(
                    {
                        "id": str(record.get("id") or ""),
                        "field": field,
                        "issue": issue,
                        "current": clipped(translated_text),
                    }
                )

    english_fragment_hits: dict[str, set[str]] = {}
    english_pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]{2,}(?:\s+[A-Za-z][A-Za-z0-9+.-]{2,}){0,2}\b")
    for record in records:
        chinese = f"{record.get('title_cn') or ''}\n{record.get('abstract_cn') or ''}"
        for fragment in english_pattern.findall(chinese):
            normalized = re.sub(r"\s+", " ", fragment).strip()
            if not normalized or normalized.lower() in allowed_english_terms:
                continue
            if normalized.endswith("-") and any(term.startswith(normalized.lower()) for term in allowed_english_terms):
                continue
            if normalized.islower() and len(normalized) <= 4:
                continue
            english_fragment_hits.setdefault(normalized, set()).add(str(record.get("id") or ""))

    lines = [
        "# Translation Audit",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Paper count: `{len(records)}`",
        f"- Glossary version: `{TRANSLATION_PROMPT_VERSION}`",
        f"- Suspect translation hits: `{len(suspect_hits)}`",
        f"- Preferred-term misses: `{len(missing_preferred)}`",
        f"- Failed or skipped fields: `{len(failed_fields)}`",
        f"- Translation quality warnings: `{len(quality_hits)}`",
        "",
        "## Review Workflow",
        "",
        "1. 先看 `High-Priority Suspect Terms`，这些通常是已知错译再次出现。",
        "2. 再看 `Preferred-Term Misses`，这里是英文原文命中了术语表，但中文译文没有出现推荐译法，可能有误报。",
        "3. 最后扫 `English Fragments`，确认保留英文是否合理；合理的缩写可以加入 `allowed_english_terms`。",
        "4. 只有通用问题才写入 `scripts/translation_glossary.json`，不要为单篇做过拟合规则。",
        "",
        "## High-Priority Suspect Terms",
        "",
    ]

    if suspect_hits:
        lines.extend(["| Paper | Field | Found | Suggestion | Reason | Context |", "| --- | --- | --- | --- | --- | --- |"])
        for hit in suspect_hits[:80]:
            lines.append(
                "| "
                + " | ".join(
                    table_cell(hit[key])
                    for key in ("id", "field", "bad", "suggestion", "reason", "context")
                )
                + " |"
            )
        if len(suspect_hits) > 80:
            lines.append(f"\nOnly the first 80 suspect hits are shown; total hits: {len(suspect_hits)}.")
    else:
        lines.append("No known high-priority suspect terms were found.")

    lines.extend(["", "## Preferred-Term Misses", ""])
    if missing_preferred:
        lines.extend(["| Paper | Source term | Preferred Chinese | English title | Current Chinese title |", "| --- | --- | --- | --- | --- |"])
        for miss in missing_preferred[:80]:
            lines.append(
                "| "
                + " | ".join(
                    table_cell(miss[key])
                    for key in ("id", "term", "preferred", "title", "title_cn")
                )
                + " |"
            )
        if len(missing_preferred) > 80:
            lines.append(f"\nOnly the first 80 preferred-term misses are shown; total misses: {len(missing_preferred)}.")
    else:
        lines.append("No preferred-term misses were found.")

    lines.extend(["", "## Failed Or Skipped Fields", ""])
    if failed_fields:
        lines.extend(["| Paper | Field | Status | Error |", "| --- | --- | --- | --- |"])
        for failure in failed_fields:
            lines.append(
                "| "
                + " | ".join(table_cell(failure[key]) for key in ("id", "field", "status", "error"))
                + " |"
            )
    else:
        lines.append("No failed or skipped translation fields were found.")

    lines.extend(["", "## Translation Quality Warnings", ""])
    if quality_hits:
        lines.extend(["| Paper | Field | Issue | Current output |", "| --- | --- | --- | --- |"])
        for hit in quality_hits:
            lines.append(
                "| "
                + " | ".join(table_cell(hit[key]) for key in ("id", "field", "issue", "current"))
                + " |"
            )
    else:
        lines.append("No structural translation quality warnings were found.")

    lines.extend(["", "## English Fragments", ""])
    if english_fragment_hits:
        lines.extend(["| Fragment | Papers |", "| --- | --- |"])
        for fragment, paper_ids in sorted(english_fragment_hits.items(), key=lambda item: (-len(item[1]), item[0].lower()))[:60]:
            lines.append(f"| {table_cell(fragment)} | {table_cell(', '.join(sorted(paper_ids)))} |")
    else:
        lines.append("No unexpected English fragments were found.")

    lines.extend(["", "## Maintenance Notes", ""])
    lines.append("- 新术语优先加到 `prompt_terms`，让模型以后主动使用。")
    lines.append("- 已知错译再加到 `replacement_rules`，保证缓存命中和模型偶发输出都能被修正。")
    lines.append("- 如果只是需要人工关注但不能确定替换，加入 `audit.suspect_translations` 或 `audit.source_terms`。")
    lines.append("- 修改术语表会自动改变 `translation_prompt_version` 指纹，下一次更新会重新翻译。")
    lines.append("")
    return "\n".join(lines)


def write_audit_report(report: str, output: str | Path) -> None:
    if str(output) == "-":
        print(report)
        return
    path = Path(output)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8", newline="\n")


def build_meta(
    records: list[dict[str, Any]],
    batch_date: str,
    fetched_at: str,
    notes: list[str],
    source_mode: str,
) -> dict[str, Any]:
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
        "source": "NBER Email" if source_mode == "email" else "NBER",
        "source_mode": source_mode,
        "source_url": SOURCE_URL,
        "batch_date": batch_date,
        "paper_count": len(records),
        "failed_translations": failed_count,
        "notes": clean_notes,
    }


def candidate_ids(candidates: list[dict[str, Any]]) -> set[str]:
    return record_ids([{"id": paper_id_from_url(absolute_url(paper.get("url")), paper)} for paper in candidates])


def record_ids(records: Any) -> set[str]:
    if not isinstance(records, list):
        raise UnsafeBatchError("Paper records must be a list.")
    ids = [record.get("id") if isinstance(record, dict) else None for record in records]
    if any(not isinstance(value, str) or not re.fullmatch(r"w\d+", value) for value in ids):
        raise UnsafeBatchError("Missing or invalid NBER paper ID.")
    if len(set(ids)) != len(ids):
        raise UnsafeBatchError("Duplicate NBER paper IDs; refusing to overwrite data.")
    return set(ids)


def require_edition(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) or normalize_date(value) != value:
        raise UnsafeBatchError("Missing or invalid newsletter edition date.")
    return value


def validate_batch_coverage(new_ids: set[str], edition: str | None, existing: Any, meta: Any, archive: Any) -> None:
    edition = require_edition(edition)
    if not new_ids:
        raise UnsafeBatchError("Empty newsletter edition; refusing to overwrite data.")
    if not isinstance(meta, dict) or not isinstance(archive, list):
        raise UnsafeBatchError("Invalid stored metadata/archive; refusing to overwrite data.")
    current_ids = record_ids(existing)
    baselines = []
    if current_ids:
        current_date = require_edition(meta.get("batch_date"))
        baselines.append((current_date, current_ids))
    for entry in archive:
        if not isinstance(entry, dict):
            raise UnsafeBatchError("Invalid archive entry; refusing to overwrite data.")
        baselines.append((require_edition(entry.get("batch_date")), record_ids(entry.get("papers"))))
    for old_date, old_ids in baselines:
        if edition < old_date:
            raise UnsafeBatchError(f"Stale newsletter edition {edition} would replace newer edition {old_date}.")
        if edition == old_date and (missing := old_ids - new_ids):
            raise UnsafeBatchError(
                f"Edition {edition} would lose {len(missing)} existing paper IDs "
                f"({', '.join(sorted(missing))}); stopped before translation or writes."
            )


def unchanged_successful_batch(records: list[dict[str, Any]], existing: list[dict[str, Any]], edition: str, meta: dict[str, Any]) -> bool:
    if meta.get("batch_date") != edition or meta.get("paper_count") != len(records) or record_ids(records) != record_ids(existing):
        return False
    old_by_id = {record["id"]: record for record in existing}
    for record in records:
        old = old_by_id[record["id"]]
        if any(record.get(field) != old.get(field) for field in ("title", "authors", "abstract", "url", "public_date")):
            return False
        if old.get("translation_prompt_version") != TRANSLATION_PROMPT_VERSION:
            return False
        for field in ("title", "abstract"):
            if (old.get("translation_status") or {}).get(field) != "success" or translation_quality_issue(str(old.get(field) or ""), str(old.get(f"{field}_cn") or ""), field):
                return False
    return True


def write_snapshot(contents: dict[Path, str]) -> None:
    """Stage all outputs before publishing; roll back every replaced file on I/O error.

    Same-directory staging keeps individual replacements atomic. This is not a
    filesystem-wide transaction against power loss; the Actions commit only runs
    after a successful exit. Backups survive if an exceptional rollback fails.
    """
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    preserve_backups = False
    try:
        for path, content in contents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            for data, destination in ((content.encode("utf-8"), staged), (path.read_bytes() if path.exists() else None, backups)):
                if data is None:
                    destination[path] = None
                    continue
                with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
                    destination[path] = Path(handle.name)
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            try:
                if backups[path] is None:
                    path.unlink()
                else:
                    os.replace(backups[path], path)
            except OSError:
                preserve_backups = True
                logging.exception("Rollback failed for %s; recovery backup retained at %s.", path, backups[path])
        raise
    finally:
        for temporary in [*staged.values(), *([] if preserve_backups else backups.values())]:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def update_archive(archive: Any, records: list[dict[str, Any]], meta: dict[str, Any]) -> list[dict[str, Any]]:
    validate_batch_coverage(record_ids(records), meta.get("batch_date"), [], {}, archive)
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
    parser.add_argument("--test-email-login", action="store_true", help="Connect to IMAP, log in, and report the INBOX count.")
    parser.add_argument(
        "--audit-translations",
        action="store_true",
        help="Audit existing papers.json translations and write a Markdown report without fetching new papers.",
    )
    parser.add_argument(
        "--audit-output",
        default=str(AUDIT_PATH.relative_to(ROOT)),
        help="Markdown audit report path; use '-' to print to stdout.",
    )
    parser.add_argument(
        "--skip-audit-report",
        action="store_true",
        help="Do not write translation-audit.md after a normal update.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "email", "api"),
        default=os.environ.get("NBER_SOURCE", "auto"),
        help="Paper source: auto/email require a dated newsletter; API fails closed until edition membership is verifiable.",
    )
    parser.add_argument(
        "--email-lookback",
        type=int,
        default=positive_int_from_env("NBER_EMAIL_IMAP_LOOKBACK", DEFAULT_EMAIL_LOOKBACK),
        help="Number of recent IMAP messages to inspect when using the email source.",
    )
    parser.add_argument("--per-page", type=int, default=50, help="Legacy API page size; API updates currently fail closed without an edition manifest.")
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
    load_local_env()
    args = parse_args()

    if args.test_email_login:
        try:
            test_email_login()
        except (OSError, imaplib.IMAP4.error, RuntimeError) as exc:
            logging.error("IMAP login test failed: %s", exc)
            return 1
        return 0

    if args.audit_translations:
        records = load_json(PAPERS_PATH, [])
        if not isinstance(records, list):
            logging.error("%s is not a JSON list.", PAPERS_PATH)
            return 1
        report = build_translation_audit_report(records, TRANSLATION_GLOSSARY, utc_now_iso())
        write_audit_report(report, args.audit_output)
        logging.info("Wrote translation audit report to %s.", args.audit_output)
        return 0

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
    notes: list[str] = []
    source_mode = "api"
    candidates: list[dict[str, Any]] | None = None
    selection_mode = "api"
    initial_batch_date: str | None = None

    if args.source in {"auto", "email"}:
        if has_imap_config():
            try:
                email_result = fetch_email_candidates(max(1, args.email_lookback))
                candidates = email_result.candidates
                selection_mode = "email"
                initial_batch_date = email_result.batch_date
                source_mode = "email"
                notes.append(f"Selected {email_result.link_count} paper links from NBER newsletter edition {initial_batch_date}.")
            except UnsafeBatchError:
                raise
            except Exception as exc:  # noqa: BLE001 - auto mode should fall back to the public API.
                if args.source == "email":
                    raise
                logging.warning("Email source failed; falling back to NBER API: %s", exc)
                notes.append("Email source unavailable; attempted API fallback.")
        elif args.source == "email":
            raise RuntimeError(f"Email source requested but missing IMAP environment variables: {', '.join(IMAP_ENV_VARS)}")
        else:
            logging.info("IMAP environment variables are not fully set; using NBER API.")
            notes.append("IMAP environment variables were not fully set; used API fallback.")

    if candidates is None:
        candidates, selection_mode, initial_batch_date = fetch_api_candidates()

    existing_papers = load_json(PAPERS_PATH, [])
    existing_meta = load_json(META_PATH, {})
    existing_archive = load_json(ARCHIVE_PATH, [])
    validate_batch_coverage(candidate_ids(candidates), initial_batch_date, existing_papers, existing_meta, existing_archive)

    records, record_notes = build_records(session, candidates, fetched_at)
    notes.extend(record_notes)
    records, batch_date = refine_to_latest_public_date(records, selection_mode, initial_batch_date)

    if not records:
        raise RuntimeError("Selected paper batch is empty after detail processing; refusing to overwrite data.")
    if not batch_date:
        raise RuntimeError("Unable to determine a batch date; refusing to overwrite data.")

    validate_batch_coverage(record_ids(records), batch_date, existing_papers, existing_meta, existing_archive)
    current_entries = [entry for entry in existing_archive if entry.get("batch_date") == batch_date]
    if (unchanged_successful_batch(records, existing_papers, batch_date, existing_meta)
            and len(current_entries) == 1
            and current_entries[0].get("papers") == existing_papers
            and current_entries[0].get("paper_count") == len(existing_papers)
            and current_entries[0].get("last_updated") == existing_meta.get("last_updated")):
        logging.info("Edition %s is unchanged with successful translations; no API calls or writes needed.", batch_date)
        return 0

    cache = load_json(CACHE_PATH, {})
    if not isinstance(cache, dict):
        cache = {}
    if isinstance(existing_papers, list):
        seeded_count = seed_cache_from_existing(cache, existing_papers)
        if seeded_count:
            logging.info("Seeded %s successful translations from existing papers.json.", seeded_count)

    cache_updates = translate_records(records, cache, api_key, args.dry_run, args.model, args.translation_workers)
    cache.update(cache_updates)

    meta = build_meta(records, batch_date, fetched_at, notes, source_mode)
    logging.info(
        "Prepared %s papers for batch %s; failed translation fields: %s.",
        meta["paper_count"],
        meta["batch_date"],
        meta["failed_translations"],
    )

    if args.dry_run:
        logging.info("Dry run complete. No files were written.")
        return 0

    archive = update_archive(existing_archive, records, meta)
    snapshot = {
        path: json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        for path, value in ((PAPERS_PATH, records), (META_PATH, meta), (CACHE_PATH, cache), (ARCHIVE_PATH, archive))
    }
    report = None
    if not args.skip_audit_report:
        report = build_translation_audit_report(records, TRANSLATION_GLOSSARY, fetched_at)
        if str(args.audit_output) != "-":
            audit_path = Path(args.audit_output)
            if not audit_path.is_absolute():
                audit_path = ROOT / audit_path
            if audit_path.resolve() in {path.resolve() for path in snapshot}:
                raise UnsafeBatchError("Audit output must not replace a JSON data file.")
            snapshot[audit_path] = report
    write_snapshot(snapshot)
    if report is not None and str(args.audit_output) == "-":
        print(report)
    logging.info("Wrote %s.", ", ".join(str(path) for path in snapshot))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:  # noqa: BLE001 - top-level CLI error reporting.
        logging.exception("Update failed: %s", exc)
        raise SystemExit(1)
