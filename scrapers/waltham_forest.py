import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import (
    DEFAULT_USER_AGENT,
    DESCRIPTION_MAX_LEN,
    Job,
    classify_employment_type,
    classify_london,
    extract_main_text,
    goto_with_retry,
    parse_salary,
)

# Every posting on this site carries the same "About Us: Bursting with culture..."
# employer-branding paragraph as part of its own content (not page-level nav, so
# extract_main_text()'s <main>/<article> isolation doesn't catch it) — strip it out
# specifically, or it satisfies the culture-sector keyword filter for every job on
# the site regardless of what the job actually is.
ABOUT_US_RE = re.compile(r'About Us:.*?(?=About the role:|Key Responsibilities:|Qualifications)', re.DOTALL)


def _strip_boilerplate(text: str) -> str:
    return ABOUT_US_RE.sub('', text)

SITE_URL = "https://fa-evng-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/LBWF/"
INSTITUTION = "London Borough of Waltham Forest"

# This is a general council job board (all departments, not just culture), so
# it returns everything unfiltered here — narrowing to culture-relevant postings
# happens generically in main.py, per config.yaml's keyword_filter, which can
# also apply the same filter to other general-board sources (see INSTRUCTIONS.md).


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-GB")
        page = context.new_page()
        goto_with_retry(page, SITE_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)
        html = page.content()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li.cc-job-list__list-item")
        if not cards:
            browser.close()
            raise RuntimeError(f"{INSTITUTION}: no job cards found — site structure may have changed or access is blocked")

        parsed = []
        for card in cards:
            link = card.select_one("a.cc-job-list__item-container")
            if not link:
                continue
            title = link.get("title", "").strip() or link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href:
                continue
            url = urljoin(SITE_URL, href)

            card_text = card.get_text("\n", strip=True)

            # Card text runs fields together with no separator ("Grade: PO10 £68,784 to
            # £72,399 Full-time/Permanent Closing Date: ..."), so capture just the money
            # amount itself rather than everything after a "Salary:"/"Grade:" label.
            salary_match = re.search(r'£[\d,]+(?:\.\d+)?(?:\s*(?:to|-)\s*£?[\d,]+(?:\.\d+)?)?', card_text)
            salary_text = salary_match.group(0).strip() if salary_match else "Not listed"

            # Capture just the date token — the label and the next field (Directorate)
            # often end up on the same line with no separator once whitespace is stripped.
            closing_match = re.search(r'Closing [Dd]ate[:\s]*(\d{1,2}/\d{1,2}/\d{4})', card_text)
            closing_date = closing_match.group(1).strip() if closing_match else "Not found"

            location_match = re.search(r'(?:Directorate|Location)[:\s]*(.*)', card_text, re.IGNORECASE)
            location_text = location_match.group(1).strip() if location_match and location_match.group(1).strip() else "Waltham Forest, London"

            parsed.append({
                "title": title,
                "url": url,
                "salary_text": salary_text,
                "location_text": location_text,
                "card_text": card_text,
                "closing_date": closing_date,
            })

        jobs = []
        for item in parsed:
            # Best-effort: the listing card already has everything matches_filters()
            # needs except description, so a detail-page failure shouldn't drop the job.
            description = ""
            try:
                goto_with_retry(page, item["url"], wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1000)
                detail_soup = BeautifulSoup(page.content(), "html.parser")
                description = _strip_boilerplate(extract_main_text(detail_soup))[:DESCRIPTION_MAX_LEN]
            except Exception:
                pass

            jobs.append(Job(
                institution=INSTITUTION,
                title=item["title"],
                url=item["url"],
                salary_text=item["salary_text"],
                salary_annual_est=parse_salary(item["salary_text"]),
                location_text=item["location_text"],
                is_london=classify_london(INSTITUTION, item["location_text"]),
                employment_type=classify_employment_type(item["card_text"]),
                closing_date=item["closing_date"],
                description=description,
            ))

        browser.close()
    return jobs
