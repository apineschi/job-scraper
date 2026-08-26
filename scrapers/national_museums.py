import re

from .base import Job, scrape_link_pattern_site

INSTITUTION = "National Museums"
LINK_PATTERN = re.compile(r'/jobs/job/\d+/')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution=INSTITUTION,
        base_url="https://www.nationalmuseums.org.uk",
        listing_url_template="https://www.nationalmuseums.org.uk/jobs/",
        link_pattern=LINK_PATTERN,
        max_pages=1,
    )
