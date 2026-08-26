import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'/jobs/job/[^"\']+/\d+')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="Tate",
        base_url="https://jobsearch.tate.org.uk",
        listing_url_template="https://jobsearch.tate.org.uk/?page={page}",
        link_pattern=LINK_PATTERN,
        max_pages=3,
    )
