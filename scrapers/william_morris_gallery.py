import re

from .base import Job, classify_london, get_soup, parse_closing_date, parse_salary, visible_text

PAGE_URL = "https://www.wmgallery.org.uk/about-us/jobs-and-opportunities/"
INSTITUTION = "William Morris Gallery"

NOT_RECRUITING_PHRASE = "not recruiting at this time"


def fetch_jobs() -> list[Job]:
    """This gallery has no job-board software — the whole "jobs" page is a single,
    rarely-updated block of prose (usually just "we are not recruiting"), not a
    list of distinct postings. Best-effort: report zero jobs when that boilerplate
    is present; otherwise treat any current (non-expired) heading found under the
    "Join our team" section as one opportunity, using the page itself as the link.
    """
    soup = get_soup(PAGE_URL)
    page_text = visible_text(soup)

    if NOT_RECRUITING_PHRASE in page_text.lower():
        return []

    jobs = []
    for heading in soup.find_all(["h2", "h3"]):
        title = heading.get_text(strip=True)
        if not title or title.lower() in ("join our team", "volunteer", "work experience"):
            continue

        # Pull the paragraph text immediately following this heading to look for a
        # deadline; skip postings whose deadline has explicitly already passed.
        block_text = ""
        for sib in heading.find_next_siblings():
            if sib.name in ("h2", "h3"):
                break
            block_text += " " + sib.get_text(" ", strip=True)

        if "deadline has now passed" in block_text.lower() or "application deadline has now passed" in block_text.lower():
            continue

        deadline_match = re.search(r'Deadline[:\s]*([\d]{1,2}\s+\w+\s+\d{4})', block_text, re.IGNORECASE)
        closing_date = deadline_match.group(1).strip() if deadline_match else "Not found"

        if closing_date != "Not found":
            closing = parse_closing_date(closing_date)
            from datetime import date
            if closing and closing < date.today():
                continue  # expired but didn't match the boilerplate phrase above

        jobs.append(Job(
            institution=INSTITUTION,
            title=title,
            url=PAGE_URL,
            salary_text="Not listed",
            salary_annual_est=parse_salary(""),
            location_text="Walthamstow, London",
            is_london=classify_london(INSTITUTION, "Walthamstow, London"),
            employment_type="unknown",
            closing_date=closing_date,
        ))
    return jobs
