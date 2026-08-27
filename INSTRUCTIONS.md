# Instructions

Everyday changes to this project — filters, pausing a source, branding, adding a
new institution, and finding old jobs. This file lives at the repo root rather
than in `docs/`, so it's never served by the live dashboard site (github.com is
the only place it's readable).

All the edits below follow the same pattern: change a file locally, then commit
and push (e.g. via GitHub Desktop). The next scan (daily at 9am UTC, or run
manually from the Actions tab) picks up the change.

---

## 1. Make an institution active / inactive

1. Open `tools/filters-editor.html` directly in your browser (double-click it —
   no server needed).
2. Under **"Load your current config.yaml"**, pick the `config.yaml` file from
   your job-scraper folder so the tool knows the current state.
3. In the **Institutions** list, find the one you want and switch its dropdown
   to **Inactive** (or back to **Active**).
4. Click **Download config.yaml** (or **Copy to clipboard**), then replace the
   `config.yaml` file in your job-scraper folder with the new content.
5. Commit and push.

An inactive institution is skipped entirely during scraping (no network
requests made to it) and shows up on the dashboard as a grayed-out card
tagged **"Paused"** — it stays in the list, it just doesn't get scraped or
generate new alerts until you switch it back to Active.

---

## 2. Change the filters (salary, employment type, location, keywords)

Same tool: `tools/filters-editor.html`.

1. Load your current `config.yaml` as above.
2. Adjust **Minimum salary**, **Employment type**, **Location**, **Include
   keywords**, and/or **Exclude keywords**.
3. Download/copy the result, replace `config.yaml`, commit, push.

These filters apply to every active institution. Two sources also have their
own extra, fixed filter on top of this (not editable from the tool):
- **Waltham Forest** — only surfaces postings mentioning library, gallery, art,
  cultural, exhibitions, or museum (it's a general council job board, not a
  culture-sector one). Edit the `CULTURE_KEYWORDS` list near the top of
  `scrapers/waltham_forest.py` to change this — each entry is a
  `(regex_pattern, display_label)` pair, and both the actual filter and the
  note shown on its dashboard card are generated from this one list, so
  they can't drift out of sync.
- **ArtsJobs UK** — pre-filtered to the "Museums" category at the source, via
  the `ART_FORM_CATEGORY` constant near the top of `scrapers/artsjobs.py`
  (also used to build both the URL and the dashboard note).

Both show a note about this on their status card on the dashboard.

---

## 3. Change the branding (emoji, colour, opacity)

**Emoji and colour** (per institution): edit `notify/branding.py`, in the
`SOURCE_BRANDING` dictionary. Each entry has:
- `"emoji"` — the actual emoji shown in the email and on the dashboard (e.g. `"🖼️"`)
- `"emoji_tag"` — a short-code used for the ntfy push notification tag; must be
  a name from [ntfy's emoji list](https://docs.ntfy.sh/emojis/) (e.g. `"framed_picture"`)
- `"color"` — a hex colour used for the email background and the dashboard
  card tint (e.g. `"#fbe0e0"`)

**Card opacity** (applies to all institutions at once, on the dashboard only):
edit `docs/index.html` and search for `hexToRgba(style.color, 0.75)` — it
appears twice (status cards and job cards). Change `0.75` to any value between
`0` (fully transparent) and `1` (fully opaque).

After editing `notify/branding.py`, commit and push as usual — `docs/branding.json`
(what the dashboard actually reads) regenerates automatically on the next scan run.

---

## 4. Add a new institution

This one needs a bit of code, since every site is structured differently. The
easiest way is to ask Claude directly: give it the vacancy-listing page URL for
the institution, and mention any special filtering you want (like the Waltham
Forest keyword filter, or the ArtsJobs category filter). Claude will inspect
the real site, write a new file in `scrapers/`, register it, and add a branding
entry.

If you want to do it yourself: look at `scrapers/tate.py` for the simplest
template (a static HTML site using the shared `scrape_link_pattern_site()`
helper in `scrapers/base.py`). Then:
1. Add the new file to `scrapers/`.
2. Import it and add it to the `SOURCES` list in `scrapers/__init__.py`.
3. Add an entry for it in `SOURCE_BRANDING` in `notify/branding.py` (institution
   name, colour, emoji, listing URL).

Sites that render their listings with JavaScript need Playwright instead of a
plain HTTP fetch — see `scrapers/nhm.py` or `scrapers/national_gallery.py` for
that pattern.

---

## 5. Find previous jobs in the database

`data/seen_jobs.json` is the permanent record — every job any scraper has ever
found, going back to when that scraper was added. It's never pruned, even once
a job's closing date passes or you Archive it on the dashboard (Archive only
hides it from your browser's view of the live dashboard; the record stays here
forever).

To look through it:
- **On GitHub**: browse to `data/seen_jobs.json` in the repo — GitHub renders
  JSON with basic syntax highlighting and you can use your browser's find
  (Ctrl+F) to search titles or institutions.
- **Locally**: open the file in any text editor, or a JSON viewer if you want
  something more structured.

Each entry is keyed by the job's URL and includes institution, title, salary,
location, closing date, employment type, when it was first found
(`first_seen`), and whether it matched your filters at the time (`matched`).

The dashboard (`docs/jobs.json`, what `https://apineschi.github.io/job-scraper/`
shows) is a *derived*, temporary view — only currently-open, filter-matching,
non-archived jobs. `data/seen_jobs.json` is the real archive.
