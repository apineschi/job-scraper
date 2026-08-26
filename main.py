import json
import os
import traceback

import yaml

from notify.email import format_digest
from notify.ntfy import send_push
from scrapers import SOURCES
from scrapers.base import matches_filters, now_iso

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
SEEN_JOBS_PATH = os.path.join(ROOT, "data", "seen_jobs.json")
STATUS_PATH = os.path.join(ROOT, "docs", "status.json")
JOBS_PATH = os.path.join(ROOT, "docs", "jobs.json")
MAX_RECENT_JOBS = 100


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_scrapers(previous_status: dict) -> tuple[list, list]:
    """Run every registered scraper, isolating failures so one broken source never
    stops the others. Returns (all_jobs, status_entries).
    """
    all_jobs = []
    status_entries = []
    checked_at = now_iso()

    for module in SOURCES:
        source_name = module.__name__.rsplit(".", 1)[-1]
        prev = previous_status.get(source_name, {})
        try:
            jobs = module.fetch_jobs()
            all_jobs.extend(jobs)
            status_entries.append({
                "source": source_name,
                "institution": jobs[0].institution if jobs else source_name,
                "status": "ok",
                "error": None,
                "checked_at": checked_at,
                "last_success": checked_at,
                "jobs_found": len(jobs),
            })
        except Exception as e:
            print(f"[{source_name}] FAILED: {e}")
            traceback.print_exc()
            status_entries.append({
                "source": source_name,
                "institution": prev.get("institution", source_name),
                "status": "error",
                "error": str(e),
                "checked_at": checked_at,
                "last_success": prev.get("last_success"),
                "jobs_found": 0,
            })

    return all_jobs, status_entries


def main():
    config = load_config()
    filters = config.get("filters", {})

    seen_jobs = load_json(SEEN_JOBS_PATH, {})
    previous_status = {entry["source"]: entry for entry in load_json(STATUS_PATH, [])}

    all_jobs, status_entries = run_scrapers(previous_status)

    new_matches = []
    for job in all_jobs:
        is_new = job.url not in seen_jobs
        if is_new:
            job.first_seen = now_iso()
            matched = matches_filters(job, filters)
            record = job.to_dict()
            record["matched"] = matched
            seen_jobs[job.url] = record
            if matched:
                new_matches.append(job)
        # Already-seen jobs are left untouched in the store (dedupe, no re-notify).

    save_json(SEEN_JOBS_PATH, seen_jobs)
    save_json(STATUS_PATH, status_entries)

    recent_matches = sorted(
        (v for v in seen_jobs.values() if v.get("matched")),
        key=lambda v: v.get("first_seen", ""),
        reverse=True,
    )[:MAX_RECENT_JOBS]
    save_json(JOBS_PATH, recent_matches)

    digest = format_digest(new_matches)
    print(digest)

    if new_matches:
        send_push(new_matches)


if __name__ == "__main__":
    main()
