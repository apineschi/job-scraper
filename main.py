import json
import os
import re
import sys
import traceback
from dataclasses import fields
from datetime import date, datetime, timezone

import yaml

from notify.branding import DEFAULT_STYLE, INSTITUTION_STYLE, SOURCE_BRANDING
from notify.email import format_digest, format_digest_html
from notify.ntfy import send_push
from scrapers import SOURCES
from scrapers.base import Job, format_long_date, matches_filters, now_iso, parse_closing_date

JOB_FIELD_NAMES = {f.name for f in fields(Job)}

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
SEEN_JOBS_PATH = os.path.join(ROOT, "data", "seen_jobs.json")
STATUS_PATH = os.path.join(ROOT, "docs", "status.json")
JOBS_PATH = os.path.join(ROOT, "docs", "jobs.json")
BRANDING_PATH = os.path.join(ROOT, "docs", "branding.json")
EMAIL_HTML_PATH = os.path.join(ROOT, "email_digest.html")
# This only bounds pathological growth — real coverage comes from the closing-date
# expiry filter, which already keeps the list to "currently open" postings. With
# 15 sources (Cambridge alone regularly finds 100+), the old cap of 100 was
# silently hiding whole institutions from the dashboard's job list/filter.
MAX_RECENT_JOBS = 1000


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


def normalize_closing_date(record_or_job) -> str | None:
    """Reparse whatever's currently in .closing_date (raw scraped text, or our own
    previously-applied long format — both parse fine, see scrapers/base.py) and
    rewrite it to the long form ("Sunday, 12 August 2026"). Returns the ISO date
    string for storage, or None if genuinely unparseable (left as original text).
    """
    is_job = hasattr(record_or_job, "closing_date")
    text = record_or_job.closing_date if is_job else record_or_job.get("closing_date", "")
    closing = parse_closing_date(text)
    if closing:
        long_text = format_long_date(closing)
        if is_job:
            record_or_job.closing_date = long_text
        else:
            record_or_job["closing_date"] = long_text
    return closing.isoformat() if closing else None


def run_scrapers(previous_status: dict, disabled_sources: set) -> tuple[list, list]:
    """Run every registered, non-disabled scraper, isolating failures so one broken
    source never stops the others. Returns (all_jobs, status_entries).
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

        if source_name in disabled_sources:
            status_entries.append({
                "source": source_name,
                "institution": display_name,
                "status": "inactive",
                "error": None,
                "checked_at": checked_at,
                "last_success": prev.get("last_success"),
                "jobs_found": 0,
            })
            continue

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


def _institutions_for_sources(source_keys) -> set:
    return {
        SOURCE_BRANDING[src]["institution"]
        for src in (source_keys or [])
        if src in SOURCE_BRANDING
    }


def dedupe_job_boards(all_jobs: list, job_board_sources: list) -> list:
    """Job-board/aggregator sources (config.yaml's job_board_sources — e.g.
    National Museums, ArtsJobs UK) surface postings already sourced directly from
    other institutions in this project. Drop a job-board listing when its title
    exactly matches (case-insensitive) a job already found from a different,
    non-job-board institution this run — keeps the direct source's listing
    instead of double-notifying for the same underlying vacancy.
    """
    job_board_institutions = _institutions_for_sources(job_board_sources)
    if not job_board_institutions:
        return all_jobs

    direct_titles = {
        job.title.strip().lower()
        for job in all_jobs
        if job.institution not in job_board_institutions
    }
    return [
        job for job in all_jobs
        if not (job.institution in job_board_institutions and job.title.strip().lower() in direct_titles)
    ]


def format_keyword_note(keywords: list) -> str | None:
    keywords = [k for k in keywords if k]
    if not keywords:
        return None
    if len(keywords) == 1:
        return f"Filtered to jobs mentioning {keywords[0]}"
    return f"Filtered to jobs mentioning {', '.join(keywords[:-1])}, or {keywords[-1]}"


def _keyword_pattern(keywords: list):
    keywords = [k for k in keywords if k]
    if not keywords:
        return None
    return re.compile(r'\b(?:' + '|'.join(re.escape(k) for k in keywords) + r')\b', re.IGNORECASE)


def _passes_keyword_filter(job, filtered_institutions: set, pattern) -> bool:
    if not pattern or job.institution not in filtered_institutions:
        return True
    return bool(pattern.search(f"{job.title} {job.location_text} {job.description}"))


def apply_keyword_filter(all_jobs: list, keyword_filter: dict) -> list:
    """Some general job boards (council sites, universities — not culture-sector
    specific) are pre-filtered to only surface postings that look relevant,
    per config.yaml's keyword_filter. Applies to whichever institutions are
    listed there (by source/module name), leaving everyone else untouched.
    """
    filtered_institutions = _institutions_for_sources(keyword_filter.get("sources") or [])
    pattern = _keyword_pattern(keyword_filter.get("keywords") or [])
    return [job for job in all_jobs if _passes_keyword_filter(job, filtered_institutions, pattern)]


def recompute_matched_for_seen(seen_jobs: dict, filters: dict, keyword_filter: dict) -> None:
    """A record's "matched" flag is set once at first_seen time and otherwise
    never touched — so any change to config.yaml's filters (salary_min, keyword
    lists, keyword_filter's sources/keywords, ...) would otherwise only affect
    jobs scraped *after* the change, silently leaving already-archived jobs on
    the old verdict forever. Every field matches_filters()/_passes_keyword_filter()
    need is already stored on the record (it's exactly job.to_dict() plus
    "matched"/"closing_date_iso"), so this reconstructs an equivalent Job and
    re-runs the *exact* same checks used for freshly scraped jobs — a full
    recompute, safe to promote or demote either way. Mutates in place.
    """
    filtered_institutions = _institutions_for_sources(keyword_filter.get("sources") or [])
    pattern = _keyword_pattern(keyword_filter.get("keywords") or [])

    for record in seen_jobs.values():
        job_kwargs = {k: v for k, v in record.items() if k in JOB_FIELD_NAMES}
        pseudo_job = Job(**job_kwargs)
        record["matched"] = (
            matches_filters(pseudo_job, filters)
            and _passes_keyword_filter(pseudo_job, filtered_institutions, pattern)
        )


def build_source_branding(keyword_filter: dict) -> dict:
    """Merge the static per-source branding with each source's own filter note:
    either a scraper module's FILTER_NOTE constant (e.g. ArtsJobs' category
    filter), or — for sources listed in config.yaml's keyword_filter — a note
    generated fresh from that config each run. Either way the dashboard's filter
    description is derived from the actual filtering configuration, not a
    hand-maintained copy that can drift out of sync.
    """
    keyword_note = format_keyword_note(keyword_filter.get("keywords") or [])
    keyword_sources = set(keyword_filter.get("sources") or [])

    merged = {}
    for module in SOURCES:
        source_name = module.__name__.rsplit(".", 1)[-1]
        style = dict(SOURCE_BRANDING.get(source_name, DEFAULT_STYLE))
        filter_note = getattr(module, "FILTER_NOTE", None)
        if source_name in keyword_sources and keyword_note:
            filter_note = keyword_note
        if filter_note:
            style["filter_note"] = filter_note
        merged[source_name] = style
    return merged


def main():
    config = load_config()
    filters = config.get("filters", {})
    disabled_sources = set(config.get("disabled_sources") or [])
    job_board_sources = config.get("job_board_sources") or []
    keyword_filter = config.get("keyword_filter") or {}
    push_enabled = config.get("push_notifications_enabled", True)

    seen_jobs = load_json(SEEN_JOBS_PATH, {})
    previous_status = {entry["source"]: entry for entry in load_json(STATUS_PATH, [])}

    # Recompute closing_date_iso (and the normalized long-form display text) for
    # every record each run rather than only when missing — cheap (pure string
    # parsing, no network calls), and self-heals if a git merge of this JSON file
    # (bot-committed scan results vs. manual edits) ever drops or staples in a
    # stale value for some records, as happened once.
    for record in seen_jobs.values():
        record["closing_date_iso"] = normalize_closing_date(record)

    recompute_matched_for_seen(seen_jobs, filters, keyword_filter)

    all_jobs, status_entries = run_scrapers(previous_status, disabled_sources)
    all_jobs = dedupe_job_boards(all_jobs, job_board_sources)
    all_jobs = apply_keyword_filter(all_jobs, keyword_filter)

    new_matches = []
    for job in all_jobs:
        is_new = job.url not in seen_jobs
        if is_new:
            job.first_seen = now_iso()
            closing_iso = normalize_closing_date(job)  # rewrites job.closing_date to the long form in place
            matched = matches_filters(job, filters)
            record = job.to_dict()
            record["matched"] = matched
            record["closing_date_iso"] = closing_iso
            seen_jobs[job.url] = record
            if matched:
                new_matches.append(job)
        # Already-seen jobs are left untouched in the store (dedupe, no re-notify).

    save_json(SEEN_JOBS_PATH, seen_jobs)
    save_json(STATUS_PATH, status_entries)
    save_json(BRANDING_PATH, {
        "institutions": INSTITUTION_STYLE,
        "sources": build_source_branding(keyword_filter),
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
        if push_enabled:
            send_push(new_matches)
        else:
            print(
                "Push notifications are suppressed (push_notifications_enabled: false "
                "in config.yaml) — skipping ntfy push. See INSTRUCTIONS.md to re-enable.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
