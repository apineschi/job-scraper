import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'/jobs/\d+-')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="King's College London",
        base_url="https://www.kcl.ac.uk",
        listing_url_template="https://www.kcl.ac.uk/jobs/search?term=&page={page}",
        link_pattern=LINK_PATTERN,
        max_pages=3,
    )
