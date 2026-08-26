import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, parse_salary

SITE_URL = "https://fa-evng-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/LBWF/"
INSTITUTION = "London Borough of Waltham Forest"

# General council job board, not culture-sector — only surface postings that look
# culture/heritage-related in title or listing text, per explicit user request.
# Word-boundary matched: a plain substring check on "art" false-positives on
# ordinary words like "Partner" or "Department".
CULTURE_KEYWORD_RE = re.compile(r'\b(?:librar(?:y|ies)|galler(?:y|ies)|arts?|cultural?)\b', re.IGNORECASE)


def _matches_culture_keywords(*texts: str) -> bool:
    combined = " ".join(t or "" for t in texts)
    return bool(CULTURE_KEYWORD_RE.search(combined))


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-GB")
        page = context.new_page()
        page.goto(SITE_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li.cc-job-list__list-item")
    if not cards:
        raise RuntimeError(f"{INSTITUTION}: no job cards found — site structure may have changed or access is blocked")

    jobs = []
    for card in cards:
        link = card.select_one("a.cc-job-list__item-container")
        if not link:
            continue
        title = link.get("title", "").strip() or link.get_text(strip=True)
        url = link.get("href", "")
        if not title or not url:
            continue

        card_text = card.get_text("\n", strip=True)
        if not _matches_culture_keywords(title, card_text):
            continue

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

        jobs.append(Job(
            institution=INSTITUTION,
            title=title,
            url=url,
            salary_text=salary_text,
            salary_annual_est=parse_salary(salary_text),
            location_text=location_text,
            is_london=classify_london(INSTITUTION, location_text),
            employment_type=classify_employment_type(card_text),
            closing_date=closing_date,
        ))
    return jobs
