import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

LONDON_KEYWORDS = [
    "london", "bankside", "millbank", "southwark", "bloomsbury", "kensington",
    "westminster", "camden", "islington", "hackney", "greenwich", "lambeth",
    "cromwell road", "queen elizabeth olympic park", "st thomas", "guy's",
    "waterloo", "barbican", "south bank", "southbank", "belvedere road",
]
NON_LONDON_KEYWORDS = [
    "liverpool", "st ives", "st. ives", "manchester", "leeds", "birmingham",
    "cardiff", "edinburgh", "glasgow", "bristol", "york",
]


@dataclass
class Job:
    institution: str
    title: str
    url: str
    salary_text: str = "Not listed"
    salary_annual_est: int = 0
    location_text: str = "Not listed"
    is_london: Optional[bool] = None
    employment_type: str = "unknown"  # full_time | part_time | both | unknown
    closing_date: str = "Not found"
    first_seen: str = ""

    def to_dict(self):
        return asdict(self)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_html(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def get_soup(url: str, timeout: int = 20) -> BeautifulSoup:
    return BeautifulSoup(fetch_html(url, timeout=timeout), "html.parser")


def visible_text(soup: BeautifulSoup) -> str:
    """soup.get_text() includes <script>/<style> contents (they're text nodes too),
    which can leak stray words like "location" from embedded JS into label regexes.
    Strip them first.
    """
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def parse_salary(text: str) -> int:
    """Best-effort estimated annual salary from free text (handles k-suffix and hourly rates)."""
    if not text:
        return 0
    t = text.lower().replace(",", "")

    hourly = re.search(r'£?\s*(\d+(?:\.\d+)?)\s*(?:per\s*hour|/\s*hr|an?\s*hour)', t)
    if hourly:
        rate = float(hourly.group(1))
        return int(rate * 37.5 * 52)

    k_vals = [float(v) * 1000 for v in re.findall(r'£?\s*(\d+(?:\.\d+)?)\s*k\b', t)]
    if k_vals:
        return int(max(k_vals))

    numbers = [int(n) for n in re.findall(r'\d{4,6}', t) if int(n) > 1000]
    if numbers:
        return max(numbers)

    return 0


def classify_london(institution: str, location_text: str) -> Optional[bool]:
    text = f"{institution} {location_text or ''}".lower()
    for kw in NON_LONDON_KEYWORDS:
        if kw in text:
            return False
    for kw in LONDON_KEYWORDS:
        if kw in text:
            return True
    # Every institution scraped in this project is London-based unless proven otherwise.
    return True


def classify_employment_type(text: str) -> str:
    if not text:
        return "unknown"
    t = text.lower()
    has_ft = "full time" in t or "full-time" in t
    has_pt = "part time" in t or "part-time" in t
    if has_ft and has_pt:
        return "both"
    if has_ft:
        return "full_time"
    if has_pt:
        return "part_time"
    return "unknown"


def scan_common_fields(page_text: str):
    """Regex-scan a job detail page's visible text for salary/location/closing date/employment type.

    Works by matching a known label followed by its value on the same rendered line —
    resilient to markup/class changes since it keys off visible text, not CSS structure.
    """
    salary_match = re.search(r'Salary[:\s]*(.*)', page_text, re.IGNORECASE)
    salary_text = salary_match.group(1).strip() if salary_match and salary_match.group(1).strip() else "Not listed"

    location_match = re.search(r'Location[:\s]*(.*)', page_text, re.IGNORECASE)
    location_text = location_match.group(1).strip() if location_match and location_match.group(1).strip() else "Not listed"

    deadline_match = re.search(
        r'(?:Application deadline|Closing date|Apply by)[:\s]*(.*)', page_text, re.IGNORECASE
    )
    closing_date = deadline_match.group(1).strip() if deadline_match and deadline_match.group(1).strip() else "Not found"

    employment_type = classify_employment_type(page_text)

    return salary_text, location_text, closing_date, employment_type


def scrape_link_pattern_site(
    institution: str,
    base_url: str,
    listing_url_template: str,
    link_pattern: "re.Pattern",
    max_pages: int = 1,
    start_page: int = 1,
    title_from_href: bool = False,
) -> list[Job]:
    """Generic scraper for sites where job links can be found by a stable href pattern
    on one or more listing pages, with per-field details pulled from each job's detail page.
    """
    links: dict[str, str] = {}
    for page_num in range(start_page, start_page + max_pages):
        url = listing_url_template.format(page=page_num)
        try:
            soup = get_soup(url)
        except requests.RequestException:
            break
        found_any = False
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not link_pattern.search(href):
                continue
            full_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
            if full_url in links:
                continue
            title = _title_from_href(href) if title_from_href else a.get_text(strip=True)
            if title:
                links[full_url] = title
                found_any = True
        if not found_any and page_num > start_page:
            break

    if not links:
        raise RuntimeError(f"{institution}: no job links found — site structure may have changed or access is blocked")

    jobs = []
    for url, title in links.items():
        time.sleep(0.4)  # be a polite scraper — avoid tripping rate limits on daily runs
        try:
            soup = get_soup(url)
        except requests.RequestException:
            continue

        clean_title = _best_title(soup, title, institution)
        page_text = visible_text(soup)

        salary_text, location_text, closing_date, employment_type = scan_common_fields(page_text)
        jobs.append(Job(
            institution=institution,
            title=clean_title,
            url=url,
            salary_text=salary_text,
            salary_annual_est=parse_salary(salary_text),
            location_text=location_text,
            is_london=classify_london(institution, location_text),
            employment_type=employment_type,
            closing_date=closing_date,
        ))
    return jobs


BOILERPLATE_TITLES = {"full information", "view", "apply", "apply now", "read more", "job profile", ""}


def _best_title(soup: BeautifulSoup, candidate: str, institution: str) -> str:
    """Prefer the listing-page title (from link text or href) unless it's clearly
    unusable — either boilerplate link text ("Full information", "View") or a giant
    concatenated blob some sites stuff into an anchor's full text content. Only then
    fall back to the detail page's <h1>, and only if that h1 isn't just the site's
    own generic heading (e.g. the institution name repeated on every page).
    """
    candidate = (candidate or "").strip()
    needs_fallback = (not candidate) or candidate.lower() in BOILERPLATE_TITLES or len(candidate) > 100
    if not needs_fallback:
        return candidate

    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""
    if h1_text and h1_text.lower() != institution.lower():
        return h1_text

    return candidate[:100] if candidate else "Untitled"


def _title_from_href(href: str) -> str:
    from urllib.parse import urlparse, parse_qs, unquote_plus
    query = parse_qs(urlparse(href).query)
    if "t" in query and query["t"]:
        return unquote_plus(query["t"][0]).strip()
    return ""


def matches_filters(job: Job, filters: dict) -> bool:
    """Apply user-configured filters to a Job. Unknown/missing data passes through
    rather than being excluded, since a false negative (hiding a real match) is worse
    than a false positive (showing one extra job) for an alerting app.
    """
    salary_min = filters.get("salary_min") or 0
    if salary_min and job.salary_annual_est and job.salary_annual_est < salary_min:
        return False

    employment_type = filters.get("employment_type", "any")
    if employment_type and employment_type != "any":
        if job.employment_type not in ("unknown", "both", employment_type):
            return False

    location = filters.get("location", "any")
    if location == "london" and job.is_london is False:
        return False
    if location == "outside_london" and job.is_london is True:
        return False

    text = f"{job.title} {job.institution}".lower()

    for kw in filters.get("exclude_keywords") or []:
        if kw.strip() and kw.strip().lower() in text:
            return False

    include_keywords = [kw.strip().lower() for kw in (filters.get("include_keywords") or []) if kw.strip()]
    if include_keywords and not any(kw in text for kw in include_keywords):
        return False

    return True
