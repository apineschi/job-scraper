import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'/jobs/search/\d+')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="ArtsJobs UK",
        base_url="https://www.artsjobs.org.uk",
        listing_url_template="https://www.artsjobs.org.uk/jobs/search?art_form=Museums&page={page}",
        link_pattern=LINK_PATTERN,
        max_pages=3,
        start_page=0,
    )
