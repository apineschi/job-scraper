import requests

from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, parse_salary

POSTINGS_URL = "https://southbankcentre.pinpointhq.com/postings.json"


def _estimate_annual_salary(posting: dict) -> int:
    minimum = posting.get("compensation_minimum")
    frequency = (posting.get("compensation_frequency") or "").lower()
    if minimum:
        if frequency == "year":
            return int(minimum)
        if frequency == "hour":
            return int(minimum * 37.5 * 52)
    return parse_salary(posting.get("compensation") or "")


def fetch_jobs() -> list[Job]:
    resp = requests.get(POSTINGS_URL, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=20)
    resp.raise_for_status()
    postings = resp.json().get("data", [])

    if not postings:
        raise RuntimeError("Southbank Centre: postings.json returned no data — API shape may have changed")

    jobs = []
    for posting in postings:
        location = posting.get("location") or {}
        location_text = location.get("name") or "Not listed"
        deadline_at = (posting.get("deadline_at") or "")[:10]  # YYYY-MM-DD

        jobs.append(Job(
            institution="Southbank Centre",
            title=posting.get("title", "Untitled"),
            url=posting.get("url", POSTINGS_URL),
            salary_text=posting.get("compensation") or "Not listed",
            salary_annual_est=_estimate_annual_salary(posting),
            location_text=location_text,
            is_london=classify_london("Southbank Centre", location_text),
            employment_type=classify_employment_type(posting.get("employment_type_text") or ""),
            closing_date=deadline_at or "Not found",
        ))
    return jobs
