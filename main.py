import json
import os
import sys
import traceback
from datetime import date, datetime, timezone

import yaml

from notify.branding import DEFAULT_STYLE, INSTITUTION_STYLE, SOURCE_BRANDING
from notify.email import format_digest, format_digest_html
from notify.ntfy import send_push
from scrapers import SOURCES
from scrapers.base import matches_filters, now_iso, parse_closing_date

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
SEEN_JOBS_PATH = os.path.join(ROOT, "data", "seen_jobs.json")
STATUS_PATH = os.path.join(ROOT, "docs", "status.json")
JOBS_PATH = os.path.join(ROOT, "docs", "jobs.json")
BRANDING_PATH = os.path.join(ROOT, "docs", "branding.json")
EMAIL_HTML_PATH = os.path.join(ROOT, "email_digest.html")
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
        # branding.py has a static display name for every registered source —
        # more reliable than deriving it from jobs[0], which is unavailable
        # whenever a source finds zero jobs (a legitimate outcome, not a failure).
        display_name = SOURCE_BRANDING.get(source_name, {}).get("institution", source_name)
        try:
            jobs = module.fetch_jobs()
            all_jobs.extend(jobs)
            status_entries.append({
                "source": source_name,
                "institution": display_name,
                "status": "ok",
                "error": None,
                "checked_at": checked_at,
                "last_success": checked_at,
                "jobs_found": len(jobs),
            })
        except Exception as e:
            # stderr, not stdout: the workflow captures stdout verbatim into the
            # user-facing email body, and scraper failures belong in the Action log
            # and the status dashboard, not in an alert email about new jobs.
            print(f"[{source_name}] FAILED: {e}", file=sys.stderr)
            traceback.print_exc()
            status_entries.append({
                "source": source_name,
                "institution": display_name,
                "status": "error",
                "error": str(e),
                "checked_at": checked_at,
                "last_success": prev.get("last_success"),
                "jobs_found": 0,
            })

    return all_jobs, status_entries


# Aggregator boards surface postings already sourced directly from other
# institutions in this project — dedupe them against the direct sources.
AGGREGATOR_SOURCES = {"National Museums", "ArtsJobs UK"}


def dedupe_aggregators(all_jobs: list) -> list:
    """Drop an aggregator's listing when its title exactly matches (case-insensitive)
    a job already found from a different, non-aggregator institution this run —
    keeps the direct source's listing instead of double-notifying for the same
    underlying vacancy (e.g. National Museums re-listing a National Gallery role).
    """
    direct_titles = {
        job.title.strip().lower()
        for job in all_jobs
        if job.institution not in AGGREGATOR_SOURCES
    }
    return [
        job for job in all_jobs
        if not (job.institution in AGGREGATOR_SOURCES and job.title.strip().lower() in direct_titles)
    ]


def main():
    config = load_config()
    filters = config.get("filters", {})

    seen_jobs = load_json(SEEN_JOBS_PATH, {})
    previous_status = {entry["source"]: entry for entry in load_json(STATUS_PATH, [])}

    # Recompute closing_date_iso for every record each run rather than only when
    # missing — cheap (pure string parsing, no network calls), and self-heals if a
    # git merge of this JSON file (bot-committed scan results vs. manual edits)
    # ever drops or staples in a stale value for some records, as happened once.
    for record in seen_jobs.values():
        closing = parse_closing_date(record.get("closing_date", ""))
        record["closing_date_iso"] = closing.isoformat() if closing else None

    all_jobs, status_entries = run_scrapers(previous_status)
    all_jobs = dedupe_aggregators(all_jobs)

    new_matches = []
    for job in all_jobs:
        is_new = job.url not in seen_jobs
        if is_new:
            job.first_seen = now_iso()
            matched = matches_filters(job, filters)
            record = job.to_dict()
            record["matched"] = matched
            closing = parse_closing_date(job.closing_date)
            record["closing_date_iso"] = closing.isoformat() if closing else None
            seen_jobs[job.url] = record
            if matched:
                new_matches.append(job)
        # Already-seen jobs are left untouched in the store (dedupe, no re-notify).

    save_json(SEEN_JOBS_PATH, seen_jobs)
    save_json(STATUS_PATH, status_entries)
    save_json(BRANDING_PATH, {
        "institutions": INSTITUTION_STYLE,
        "sources": SOURCE_BRANDING,
        "default": DEFAULT_STYLE,
    })

    # Jobs past their closing date drop off the *displayed* list (docs/jobs.json)
    # but stay in data/seen_jobs.json forever — that file is the research archive,
    # this one is just "what's currently open". A closing date we can't parse
    # (missing/malformed) is treated as "unknown, don't assume expired".
    today = datetime.now(timezone.utc).date()

    def is_expired(record: dict) -> bool:
        iso = record.get("closing_date_iso")
        return bool(iso) and date.fromisoformat(iso) < today

    recent_matches = sorted(
        (v for v in seen_jobs.values() if v.get("matched") and not is_expired(v)),
        key=lambda v: v.get("first_seen", ""),
        reverse=True,
    )[:MAX_RECENT_JOBS]
    save_json(JOBS_PATH, recent_matches)

    digest = format_digest(new_matches)
    print(digest)

    with open(EMAIL_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(format_digest_html(new_matches))

    if new_matches:
        send_push(new_matches)


if __name__ == "__main__":
    main()
