import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'/careers/[a-z0-9\-]+')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="Barbican Centre",
        base_url="https://www.barbican.org.uk",
        listing_url_template="https://www.barbican.org.uk/our-story/about-us/careers",
        link_pattern=LINK_PATTERN,
        max_pages=1,
    )
