from datetime import datetime

from playwright.sync_api import sync_playwright

from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, parse_salary

SEARCH_URL = "https://royalacademyarts.current-vacancies.com/Careers/RA-vacancy-search-page-3191"
INSTITUTION = "Royal Academy of Arts"


def _field(record: dict, suffix: str) -> str:
    """Eploy's custom-field keys carry a tenant-specific numeric prefix
    (e.g. "37512031_Salary") — match by suffix instead of hardcoding the prefix.
    """
    for key, value in record.items():
        if key.endswith(suffix):
            return value or ""
    return ""


def _format_expiry(raw: str) -> str:
    # Eploy returns DD/MM/YYYY; reformat to match the rest of the app's style.
    try:
        return datetime.strptime(raw, "%d/%m/%Y").strftime("%d %B %Y")
    except (ValueError, TypeError):
        return raw or "Not found"


def fetch_jobs() -> list[Job]:
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-GB")
        page = context.new_page()

        def on_response(response):
            if "SearchVacancies" in response.url and "Count" not in response.url:
                try:
                    body = response.json()
                    if body.get("OK") and body.get("Data"):
                        records.extend(body["Data"])
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2500)
        browser.close()

    if not records:
        raise RuntimeError(f"{INSTITUTION}: no job listings returned — site structure may have changed or access is blocked")

    jobs = []
    seen_ids = set()
    for record in records:
        vacancy_id = record.get("VacancyID")
        if vacancy_id in seen_ids:
            continue
        seen_ids.add(vacancy_id)

        title = record.get("VacancyTitle", "Untitled")
        url = record.get("ApplyLink") or SEARCH_URL
        salary_text = _field(record, "_Salary") or "Not listed"
        location_text = record.get("Location") or "Not listed"
        contract_type = _field(record, "_ContractType")
        closing_date = _format_expiry(record.get("ExpiryDate", ""))

        jobs.append(Job(
            institution=INSTITUTION,
            title=title,
            url=url,
            salary_text=salary_text,
            salary_annual_est=parse_salary(salary_text),
            location_text=location_text,
            is_london=classify_london(INSTITUTION, location_text),
            employment_type=classify_employment_type(f"{contract_type} {record.get('JobDescription', '')}"),
            closing_date=closing_date,
        ))
    return jobs
