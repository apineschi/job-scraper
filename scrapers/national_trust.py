import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, parse_salary

SEARCH_URL = "https://careers.nationaltrust.org.uk/OA_HTML/a/#/search"
DETAIL_URL_TEMPLATE = "https://careers.nationaltrust.org.uk/OA_HTML/a/#/vacancy-detail/{req_id}"
INSTITUTION = "National Trust"

VACANCY_LINK_RE = re.compile(r'#/vacancy-detail/(\d+)')


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-GB")
        page = context.new_page()
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".item-grid")
    if not cards:
        raise RuntimeError(f"{INSTITUTION}: no job cards found — site structure may have changed or access is blocked")

    jobs = []
    seen_ids = set()
    for card in cards:
        link = card.find("a", href=VACANCY_LINK_RE)
        if not link:
            continue
        match = VACANCY_LINK_RE.search(link["href"])
        req_id = match.group(1)
        if req_id in seen_ids:
            continue
        seen_ids.add(req_id)

        card_text = card.get_text("\n", strip=True)
        lines = [l for l in card_text.split("\n") if l.strip()]
        title = lines[0] if lines else "Untitled"

        salary_match = re.search(r'[\d,]+\s*pa\b', card_text)
        salary_text = salary_match.group(0).strip() if salary_match else "Not listed"

        location_match = re.search(r'\n([A-Za-z][^\n]*)\n[\d.]+\s*mi from', card_text)
        location_text = location_match.group(1).strip() if location_match else "Not listed"

        closing_match = re.search(r'Ends:\s*([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)', card_text)
        closing_date = closing_match.group(1).strip() if closing_match else "Not found"

        jobs.append(Job(
            institution=INSTITUTION,
            title=title,
            url=DETAIL_URL_TEMPLATE.format(req_id=req_id),
            salary_text=salary_text,
            salary_annual_est=parse_salary(salary_text),
            location_text=location_text,
            is_london=classify_london(INSTITUTION, location_text, default=None),
            employment_type=classify_employment_type(card_text),
            closing_date=closing_date,
        ))
    return jobs
