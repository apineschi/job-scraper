import re
from datetime import date, timedelta
from urllib.parse import parse_qs, unquote_plus, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import (
    DEFAULT_USER_AGENT,
    Job,
    classify_london,
    get_soup,
    parse_salary,
    scan_common_fields,
    visible_text,
)

LINK_PATTERN = re.compile(r'current-vacancies\.com/Jobs/FeedLink/')
LISTING_URL = "https://www.vam.ac.uk/vacancies"
INSTITUTION = "Victoria and Albert Museum"

# This ATS only renders a relative "will close in N days" sentence — filled in
# client-side (the raw HTML has literal "{x} days" placeholders) and with no
# absolute date anywhere on the page. Convert it to a real date at scrape time.
RELATIVE_CLOSE_RE = re.compile(r'will close\s*(?:in\s*)?(today|tomorrow|\d+\s*days?)', re.IGNORECASE)


def _parse_relative_closing(page_text: str) -> str:
    match = RELATIVE_CLOSE_RE.search(page_text)
    if not match:
        return "Not found"

    token = match.group(1).lower()
    if token == "today":
        days = 0
    elif token == "tomorrow":
        days = 1
    else:
        days = int(re.search(r'\d+', token).group(0))

    return (date.today() + timedelta(days=days)).strftime("%d %B %Y")


def _discover_job_links() -> dict[str, str]:
    soup = get_soup(LISTING_URL)
    links: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not LINK_PATTERN.search(href):
            continue
        query = parse_qs(urlparse(href).query)
        title = unquote_plus(query["t"][0]).strip() if query.get("t") else ""
        if title and href not in links:
            links[href] = title
    return links


def fetch_jobs() -> list[Job]:
    links = _discover_job_links()
    if not links:
        raise RuntimeError(f"{INSTITUTION}: no job links found — site structure may have changed or access is blocked")

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = context.new_page()

        for url, title in links.items():
            # networkidle never settles on these FeedLink redirect pages (some
            # persistent background polling) — domcontentloaded + an explicit
            # wait for the client-side template fill-in is more reliable here.
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            soup = BeautifulSoup(page.content(), "html.parser")
            page_text = visible_text(soup)

            salary_text, location_text, _, employment_type = scan_common_fields(page_text)
            closing_date = _parse_relative_closing(page_text)

            jobs.append(Job(
                institution=INSTITUTION,
                title=title,
                url=url,
                salary_text=salary_text,
                salary_annual_est=parse_salary(salary_text),
                location_text=location_text,
                is_london=classify_london(INSTITUTION, location_text),
                employment_type=employment_type,
                closing_date=closing_date,
            ))

        browser.close()
    return jobs
