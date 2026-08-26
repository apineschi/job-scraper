from .base import DEFAULT_USER_AGENT, Job, classify_employment_type, classify_london, get_soup, parse_salary

INSTITUTION = "University of Cambridge"
LISTING_URL = "https://www.cam.ac.uk/jobs/search?search_api_views_fulltext="
BASE_URL = "https://www.cam.ac.uk"


def fetch_jobs() -> list[Job]:
    soup = get_soup(LISTING_URL)
    rows = soup.select("table tbody tr")
    if not rows:
        raise RuntimeError(f"{INSTITUTION}: no vacancy rows found — site structure may have changed or access is blocked")

    jobs = []
    for row in rows:
        title_cell = row.select_one(".views-field-title")
        if not title_cell:
            continue
        link = title_cell.find("a", href=True)
        title = title_cell.get_text(strip=True)
        if not link or not title:
            continue

        href = link["href"]
        url = href if href.startswith("http") else BASE_URL + href

        location_text = row.select_one(".views-field-field-department-location")
        location_text = location_text.get_text(strip=True) if location_text else "Not listed"

        salary_cell = row.select_one(".views-field-field-salary")
        salary_text = salary_cell.get_text(strip=True) if salary_cell else "Not listed"

        closing_cell = row.select_one(".views-field-field-closing-date")
        closing_date = closing_cell.get_text(strip=True) if closing_cell else "Not found"

        jobs.append(Job(
            institution=INSTITUTION,
            title=title,
            url=url,
            salary_text=salary_text,
            salary_annual_est=parse_salary(salary_text),
            location_text=location_text,
            is_london=classify_london(INSTITUTION, location_text, default=False),
            employment_type=classify_employment_type(title_cell.parent.get_text(" ", strip=True)),
            closing_date=closing_date,
        ))
    return jobs
