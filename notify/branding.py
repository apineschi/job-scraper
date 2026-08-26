# Per-institution styling shared by the HTML email (background color) and the
# ntfy push (emoji tag, using ntfy's gemoji short-code convention). Any
# institution not listed here — e.g. a newly added scraper — falls back to
# DEFAULT_STYLE rather than erroring.

INSTITUTION_STYLE = {
    "British Museum": {"color": "#f3e6d8", "emoji_tag": "classical_building"},
    "Tate": {"color": "#fbe0e0", "emoji_tag": "framed_picture"},
    "King's College London": {"color": "#ede0f0", "emoji_tag": "mortar_board"},
    "Victoria and Albert Museum": {"color": "#dde8f5", "emoji_tag": "gem"},
    "Barbican Centre": {"color": "#e5e5e5", "emoji_tag": "performing_arts"},
    "ArtsJobs UK": {"color": "#fbe8d6", "emoji_tag": "briefcase"},
    "Southbank Centre": {"color": "#d9f0ee", "emoji_tag": "musical_note"},
    "National Gallery": {"color": "#e0e5ec", "emoji_tag": "art"},
}

DEFAULT_STYLE = {"color": "#eeeeee", "emoji_tag": "briefcase"}


def style_for(institution: str) -> dict:
    return INSTITUTION_STYLE.get(institution, DEFAULT_STYLE)
