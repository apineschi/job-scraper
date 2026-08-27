import re

from .base import Job, scrape_link_pattern_site

LINK_PATTERN = re.compile(r'/jobs/search/\d+')

# Single source of truth for both the URL filter and the dashboard note below.
ART_FORM_CATEGORY = "Museums"
FILTER_NOTE = f"Filtered to the {ART_FORM_CATEGORY} category only"


def fetch_jobs() -> list[Job]:
    return scrape_link_pattern_site(
        institution="ArtsJobs UK",
        base_url="https://www.artsjobs.org.uk",
        listing_url_template=f"https://www.artsjobs.org.uk/jobs/search?art_form={ART_FORM_CATEGORY}&page={{page}}",
        link_pattern=LINK_PATTERN,
        max_pages=3,
        start_page=0,
    )
