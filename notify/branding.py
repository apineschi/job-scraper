# Per-source styling shared by the HTML email (background color + emoji), the ntfy
# push (emoji_tag, using ntfy's gemoji short-code convention), and the status
# dashboard (color + emoji + listing URL, via docs/branding.json which main.py
# writes from this file each run).
#
# Keyed by the scraper module's short name (e.g. "tate", matching
# module.__name__.rsplit(".", 1)[-1]) rather than the institution display name —
# that's the one identifier guaranteed to exist even for a source that has never
# successfully scraped a job yet (status.json's "institution" field falls back to
# the raw source name in that case, which wouldn't match a lookup by display name).
#
# Any source not listed here — e.g. a newly added scraper — falls back to
# DEFAULT_STYLE rather than erroring.

SOURCE_BRANDING = {
    "british_museum": {
        "institution": "British Museum",
        "color": "#f3e6d8", "emoji_tag": "classical_building", "emoji": "🏛️",
        "url": "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/job_list.aspx",
    },
    "tate": {
        "institution": "Tate",
        "color": "#fbe0e0", "emoji_tag": "framed_picture", "emoji": "🖼️",
        "url": "https://jobsearch.tate.org.uk/",
    },
    "kcl": {
        "institution": "King's College London",
        "color": "#ede0f0", "emoji_tag": "mortar_board", "emoji": "🎓",
        "url": "https://www.kcl.ac.uk/jobs/search?term=",
    },
    "vam": {
        "institution": "Victoria and Albert Museum",
        "color": "#dde8f5", "emoji_tag": "gem", "emoji": "💎",
        "url": "https://www.vam.ac.uk/vacancies",
    },
    "barbican": {
        "institution": "Barbican Centre",
        "color": "#e5e5e5", "emoji_tag": "performing_arts", "emoji": "🎭",
        "url": "https://www.barbican.org.uk/our-story/about-us/careers",
    },
    "artsjobs": {
        "institution": "ArtsJobs UK",
        "color": "#fbe8d6", "emoji_tag": "briefcase", "emoji": "💼",
        "url": "https://www.artsjobs.org.uk/jobs/search?art_form=Museums",
    },
    "southbank": {
        "institution": "Southbank Centre",
        "color": "#d9f0ee", "emoji_tag": "musical_note", "emoji": "🎵",
        "url": "https://careers.southbankcentre.co.uk/",
    },
    "national_gallery": {
        "institution": "National Gallery",
        "color": "#e0e5ec", "emoji_tag": "art", "emoji": "🎨",
        "url": "https://ce0838li.webitrent.com/ce0838li_webrecruitment/wrd/run/ETREC179GF.open?WVID=7102672HeH",
    },
}

DEFAULT_STYLE = {"institution": None, "color": "#eeeeee", "emoji_tag": "briefcase", "emoji": "💼", "url": None}

# Kept for the email/ntfy code paths, which only know the institution display name
# (from a Job record), not which scraper module produced it.
INSTITUTION_STYLE = {meta["institution"]: meta for meta in SOURCE_BRANDING.values()}


def style_for(institution: str) -> dict:
    return INSTITUTION_STYLE.get(institution, DEFAULT_STYLE)


def style_for_source(source: str) -> dict:
    return SOURCE_BRANDING.get(source, DEFAULT_STYLE)
