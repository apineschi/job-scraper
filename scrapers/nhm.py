import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import (
    DEFAULT_USER_AGENT,
    DESCRIPTION_MAX_LEN,
    Job,
    classify_london,
    extract_main_text,
    parse_salary,
    scan_common_fields,
    visible_text,
)

LISTING_URL = "https://jobs.nhm.ac.uk/Home/Job"
BASE_URL = "https://jobs.nhm.ac.uk"
INSTITUTION = "Natural History Museum"
LINK_PATTERN = re.compile(r'/Job/JobDetail\?JobId=\d+')
# The listing page has no visible pagination control (seemingly renders every
# result on one page today) — but it does self-report a total ("There are 11
# jobs matching..."). If that total ever exceeds what we actually parsed, a
# page-size limit or "load more" control we're not aware of has appeared —
# same failure shape as British Museum silently missing page 2. Fail loudly
# instead of silently under-reporting.
TOTAL_COUNT_PATTERN = re.compile(r'There are (\d+) jobs?\s+matching', re.IGNORECASE)


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-GB")
        page = context.new_page()
        page.goto(LISTING_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        soup = BeautifulSoup(page.content(), "html.parser")
        links: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not LINK_PATTERN.search(href):
                continue
            title = a.get_text(strip=True)
            full_url = href if href.startswith("http") else BASE_URL + href
            if title and full_url not in links:
                links[full_url] = title

        if not links:
            browser.close()
            raise RuntimeError(f"{INSTITUTION}: no job links found — site structure may have changed or access is blocked")

        total_match = TOTAL_COUNT_PATTERN.search(visible_text(soup))
        if total_match and int(total_match.group(1)) > len(links):
            browser.close()
            raise RuntimeError(
                f"{INSTITUTION}: page reports {total_match.group(1)} jobs but only "
                f"{len(links)} link(s) were found — a page-size limit or pagination "
                f"control may have appeared that this scraper doesn't handle yet"
            )

        jobs = []
        for url, title in links.items():
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)
            detail_soup = BeautifulSoup(page.content(), "html.parser")
            page_text = visible_text(detail_soup)
            salary_text, location_text, closing_date, employment_type = scan_common_fields(page_text)

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
                description=extract_main_text(detail_soup)[:DESCRIPTION_MAX_LEN],
            ))

        browser.close()
    return jobs
