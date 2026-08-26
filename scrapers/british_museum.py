from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, Job, classify_london, parse_salary, scan_common_fields, visible_text

LISTING_URL = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/job_list.aspx"
BASE_URL = "https://bmrecruit.ciphr-irecruit.com"


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

        soup = BeautifulSoup(page.content(), "html.parser")
        links: dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if "/vacancy/" not in href.lower() or not title:
                continue
            full_url = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
            links.setdefault(full_url, title)  # first occurrence is the real title, not "View Details »"

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
            ))

        browser.close()
    return jobs
