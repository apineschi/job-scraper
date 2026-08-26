from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, parse_salary

SEARCH_URL = "https://ce0838li.webitrent.com/ce0838li_webrecruitment/wrd/run/ETREC179GF.open?WVID=7102672HeH"
SHARE_URL_TEMPLATE = (
    "https://ce0838li.webitrent.com/ce0838li_webrecruitment/wrd/run/etrec179gf.open"
    "?WVID=7102672HeH&LANG=USA&VACANCY_ID={vac_id}"
)

ICON_TO_FIELD = {
    "location_on": "location",
    "credit_card": "salary",
    "work_outline": "basis",
}


def fetch_jobs() -> list[Job]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
        page = context.new_page()
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)

        try:
            page.click("#main-find-jobs", timeout=3000)
            page.wait_for_timeout(2000)
        except Exception:
            pass  # results already load automatically on first visit

        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()

    cards = soup.select("div.Mhr-jobDetail.Mhr-jobDetail--listItem")
    if not cards:
        raise RuntimeError("National Gallery: no job cards found — page structure may have changed or access is blocked")

    jobs = []
    for card in cards:
        vac_id = card.get("vac-id")
        title_span = card.select_one(".Mhr-jobDetailTitleLink span")
        title = title_span.get_text(strip=True) if title_span else "Untitled"

        closing_span = card.select_one(".Mhr-jobDetailClosingDate span")
        closing_date = closing_span.get_text(strip=True).replace("Apply by", "").strip() if closing_span else "Not found"

        fields = {"location": "Not listed", "salary": "Not listed", "basis": "unknown"}
        for entry in card.select(".Mhr-jobDetailEntry"):
            icon = entry.select_one(".Mhr-jobDetailEntry--icon")
            value = entry.select_one(".Mhr-jobDetailEntry--text")
            if icon and value:
                field = ICON_TO_FIELD.get(icon.get_text(strip=True))
                if field:
                    fields[field] = value.get_text(strip=True)

        url = SHARE_URL_TEMPLATE.format(vac_id=vac_id) if vac_id else SEARCH_URL

        jobs.append(Job(
            institution="National Gallery",
            title=title,
            url=url,
            salary_text=fields["salary"],
            salary_annual_est=parse_salary(fields["salary"]),
            location_text=fields["location"],
            is_london=classify_london("National Gallery", fields["location"]),
            employment_type=classify_employment_type(fields["basis"]),
            closing_date=closing_date,
        ))
    return jobs
