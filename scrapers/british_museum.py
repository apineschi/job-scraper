import re

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, DESCRIPTION_MAX_LEN, Job, classify_london, extract_main_text, parse_salary, scan_common_fields, visible_text

LISTING_URL = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/job_list.aspx"
BASE_URL = "https://bmrecruit.ciphr-irecruit.com"

# Real job links look like /Applicants/vacancy/9059/Senior-Infrastructure-Engineer
# (numeric id, then a slug). Once there's more than one page of results, the
# pager's own links ("2", "Next »", "Last »»") also contain "/vacancy/" — e.g.
# /Applicants/vacancy/10-2-1/?proximityDistance=0&proximityUnit=0 — and got
# scraped as if "2" were a job title. Requiring a pure-numeric id segment
# excludes those without needing to special-case pager link text.
JOB_LINK_PATTERN = re.compile(r'/vacancy/\d+/', re.IGNORECASE)


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # The site's server errors out (NullReferenceException in its own locale
        # lookup) without an explicit locale/Accept-Language — real browsers send
        # this by default, Playwright's default context doesn't.
        context = browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            locale="en-GB",
            timezone_id="Europe/London",
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
        )
        page = context.new_page()
        page.goto(LISTING_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        links: dict[str, str] = {}
        visited_listing_urls: set[str] = set()
        next_url = LISTING_URL
        # Follows "Next »" through however many result pages exist (capped as a
        # loop-safety net, not an expected real limit) — a second page showed up
        # for the first time once there were more than 10 open vacancies, and
        # this scraper never previously fetched anything past page 1.
        for _ in range(10):
            if next_url != LISTING_URL:
                page.goto(next_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
            visited_listing_urls.add(next_url)

            soup = BeautifulSoup(page.content(), "html.parser")
            next_href = None
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = a.get_text(strip=True)
                if title == "Next »":
                    next_href = href
                    continue
                if not JOB_LINK_PATTERN.search(href) or not title:
                    continue
                full_url = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
                links.setdefault(full_url, title)  # first occurrence is the real title, not "View Details »"

            if not next_href:
                break
            next_url = next_href if next_href.startswith("http") else BASE_URL + "/" + next_href.lstrip("/")
            if next_url in visited_listing_urls:
                break

        if not links:
            browser.close()
            raise RuntimeError("British Museum: no job links found — site structure may have changed or access is blocked")

        jobs = []
        for url, title in links.items():
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            detail_soup = BeautifulSoup(page.content(), "html.parser")
            page_text = visible_text(detail_soup)
            salary_text, location_text, closing_date, employment_type = scan_common_fields(page_text)

            jobs.append(Job(
                institution="British Museum",
                title=title,
                url=url,
                salary_text=salary_text,
                salary_annual_est=parse_salary(salary_text),
                location_text=location_text,
                is_london=classify_london("British Museum", location_text),
                employment_type=employment_type,
                closing_date=closing_date,
                description=extract_main_text(detail_soup)[:DESCRIPTION_MAX_LEN],
            ))

        browser.close()
    return jobs
