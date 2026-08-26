import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'current-vacancies\.com/Jobs/FeedLink/')


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="Victoria and Albert Museum",
        base_url="https://www.vam.ac.uk",
        listing_url_template="https://www.vam.ac.uk/vacancies",
        link_pattern=LINK_PATTERN,
        max_pages=1,
        title_from_href=True,
    )
