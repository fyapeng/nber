from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

import update_papers as updater


DEFAULT_MODEL = "kimi-k2.6"
NON_THINKING_KIMI_MODELS = {"kimi-k2.5", "kimi-k2.6"}


class TranslationService(updater.TranslationService):
    """Compatibility layer for current Kimi models without changing the updater core."""

    def __init__(self, api_key: str | None, dry_run: bool, model: str) -> None:
        super().__init__(api_key=api_key, dry_run=dry_run, model=model)
        if not self.client or dry_run:
            return

        try:
            response = self.client.models.list()
            available_models = {str(item.id) for item in response.data}
        except Exception as exc:  # noqa: BLE001 - surface API/key/region problems before the batch starts.
            raise RuntimeError(
                "Kimi API preflight failed while listing models with the existing KIMI_API_KEY. "
                "Check the key's API-platform region, permission, and balance."
            ) from exc

        if model not in available_models:
            preferred = [name for name in ("kimi-k2.6", "kimi-k2.5") if name in available_models]
            hint = f" Available preferred models: {', '.join(preferred)}." if preferred else ""
            raise RuntimeError(
                f"Kimi model {model!r} is not available to the existing KIMI_API_KEY.{hint}"
            )

        logging.info("Kimi API preflight passed; using model %s.", model)

    def translate(
        self,
        paper_id: str,
        field: str,
        source_text: str,
        cache: dict[str, Any],
    ) -> updater.TranslationResult:
        if not source_text:
            return updater.TranslationResult("", "skipped_empty", None)

        key = updater.make_cache_key(paper_id, field, source_text)
        cached = cache.get(key)
        if isinstance(cached, dict) and cached.get("translation"):
            cached_text = str(cached["translation"])
            translated = updater.apply_translation_rules(source_text, cached_text)
            issue = updater.translation_quality_issue(source_text, translated, field)
            if not issue:
                cache_entry = None
                if translated != cached_text:
                    cache_entry = {
                        **cached,
                        "translation": translated,
                        "prompt_version": updater.TRANSLATION_PROMPT_VERSION,
                        "updated_at": updater.utc_now_iso(),
                    }
                return updater.TranslationResult(translated, "success", None, key, cache_entry)
            logging.warning("Ignoring invalid cached translation for %s %s: %s", paper_id, field, issue)

        if isinstance(cached, str) and cached:
            translated = updater.apply_translation_rules(source_text, cached)
            issue = updater.translation_quality_issue(source_text, translated, field)
            if not issue:
                cache_entry = None
                if translated != cached:
                    cache_entry = {
                        "translation": translated,
                        "model": "normalized-from-cache",
                        "prompt_version": updater.TRANSLATION_PROMPT_VERSION,
                        "updated_at": updater.utc_now_iso(),
                    }
                return updater.TranslationResult(translated, "success", None, key, cache_entry)
            logging.warning("Ignoring invalid legacy cache for %s %s: %s", paper_id, field, issue)

        if self.dry_run:
            return updater.TranslationResult(source_text, "skipped_dry_run", None, key)

        if not self.client:
            return updater.TranslationResult(source_text, "skipped_no_api_key", "KIMI_API_KEY is not set.", key)

        last_error = None
        for attempt in range(1, updater.TRANSLATION_ATTEMPTS + 1):
            try:
                logging.info(
                    "Translating %s %s with %s (attempt %s/%s).",
                    paper_id,
                    field,
                    self.model,
                    attempt,
                    updater.TRANSLATION_ATTEMPTS,
                )
                request: dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": updater.ECON_TRANSLATION_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": f"请翻译以下 NBER 论文{'标题' if field == 'title' else '摘要'}：\n\n{source_text}",
                        },
                    ],
                }

                if self.model in NON_THINKING_KIMI_MODELS:
                    # K2.5/K2.6 require their fixed sampling parameters. For translation,
                    # disable thinking to reduce latency and token cost and do not send temperature=0.1.
                    request["extra_body"] = {"thinking": {"type": "disabled"}}
                else:
                    request["temperature"] = 0.1

                response = self.client.chat.completions.create(**request)
                translated = updater.apply_translation_rules(
                    source_text,
                    response.choices[0].message.content or "",
                )
                issue = updater.translation_quality_issue(source_text, translated, field)
                if issue:
                    raise RuntimeError(f"translation quality check failed: {issue}")

                return updater.TranslationResult(
                    translated,
                    "success",
                    None,
                    key,
                    {
                        "translation": translated,
                        "model": self.model,
                        "prompt_version": updater.TRANSLATION_PROMPT_VERSION,
                        "updated_at": updater.utc_now_iso(),
                    },
                )
            except Exception as exc:  # noqa: BLE001 - API clients raise several exception families.
                last_error = str(exc)
                logging.warning("Kimi translation failed for %s %s: %s", paper_id, field, last_error)
                if attempt < updater.TRANSLATION_ATTEMPTS:
                    time.sleep(updater.BACKOFF_SECONDS[attempt - 1])

        return updater.TranslationResult(source_text, "failed", last_error, key)


def translation_failure_counts() -> tuple[int, int]:
    records = updater.load_json(updater.PAPERS_PATH, [])
    if not isinstance(records, list):
        return 0, 0

    total = 0
    failed = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        statuses = record.get("translation_status") or {}
        for field in ("title", "abstract"):
            if not str(record.get(field) or "").strip():
                continue
            total += 1
            if statuses.get(field) == "failed":
                failed += 1
    return total, failed


def main() -> int:
    # Reuse the existing KIMI_API_KEY. Only the model selection changes.
    os.environ.setdefault("KIMI_MODEL", DEFAULT_MODEL)
    updater.TranslationService = TranslationService

    exit_code = updater.run()
    if exit_code != 0:
        return exit_code

    if "--dry-run" in sys.argv or "--audit-translations" in sys.argv or "--test-email-login" in sys.argv:
        return 0

    total, failed = translation_failure_counts()
    if total and failed == total:
        logging.error(
            "All %s translatable fields failed. Refusing to report a successful GitHub Actions run.",
            total,
        )
        return 3
    if failed:
        logging.warning("%s of %s translatable fields failed; keeping the partial batch for audit.", failed, total)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - top-level CLI error reporting.
        logging.exception("Update failed: %s", exc)
        raise SystemExit(1)
