from __future__ import annotations

import logging
import sys

import update_papers as updater


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
    # The updater picks the DeepSeek model from the API's live model list (see update_papers.pick_model);
    # this wrapper only refuses to report success when every translation failed.
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
        print(f"::warning::{failed} of {total} translations failed; they stay in English until the next run")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - top-level CLI error reporting.
        logging.exception("Update failed: %s", exc)
        raise SystemExit(1)
