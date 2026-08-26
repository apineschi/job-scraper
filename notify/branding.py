# Per-institution styling shared by the HTML email (background color + emoji), the
# ntfy push (emoji_tag, using ntfy's gemoji short-code convention), and the status
# dashboard (color + emoji, via docs/branding.json which main.py writes from this
# file each run). Any institution not listed here — e.g. a newly added scraper —
# falls back to DEFAULT_STYLE rather than erroring.

INSTITUTION_STYLE = {
    "British Museum": {"color": "#f3e6d8", "emoji_tag": "classical_building", "emoji": "🏛️"},
    "Tate": {"color": "#fbe0e0", "emoji_tag": "framed_picture", "emoji": "🖼️"},
    "King's College London": {"color": "#ede0f0", "emoji_tag": "mortar_board", "emoji": "🎓"},
    "Victoria and Albert Museum": {"color": "#dde8f5", "emoji_tag": "gem", "emoji": "💎"},
    "Barbican Centre": {"color": "#e5e5e5", "emoji_tag": "performing_arts", "emoji": "🎭"},
    "ArtsJobs UK": {"color": "#fbe8d6", "emoji_tag": "briefcase", "emoji": "💼"},
    "Southbank Centre": {"color": "#d9f0ee", "emoji_tag": "musical_note", "emoji": "🎵"},
    "National Gallery": {"color": "#e0e5ec", "emoji_tag": "art", "emoji": "🎨"},
}

DEFAULT_STYLE = {"color": "#eeeeee", "emoji_tag": "briefcase", "emoji": "💼"}


def style_for(institution: str) -> dict:
    return INSTITUTION_STYLE.get(institution, DEFAULT_STYLE)
