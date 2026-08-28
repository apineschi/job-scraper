# Instructions

Everyday changes to this project — filters, pausing a source, duplicate
checking, branding, adding a new institution, finding old jobs, and push
notifications. This file lives at the repo root rather than in `docs/`, so
it's never served by the live dashboard site (github.com is the only place
it's readable).

All the edits below follow the same pattern: change a file locally, then commit
and push (e.g. via GitHub Desktop). The next scan (daily at 9am UTC, or run
manually from the Actions tab) picks up the change.

> **⚠️ `tools/filters-editor.html` is a form you open in a browser — never
> edit its code directly.** Several sections below say "open the tool, load
> your config, change a field, download/copy the result." That means:
> double-click the file so it opens as a page in your browser, use the
> **Load your current config.yaml** button, change the setting *in that
> page's input fields*, then **Download config.yaml** (or **Copy to
> clipboard**) and replace the real `config.yaml` with what it generates.
>
> If you instead open `tools/filters-editor.html` in a code/text editor and
> change the text in there (e.g. editing a `value="..."` attribute), you've
> only changed what that field shows the *next* time someone opens the tool
> fresh — it never touches `config.yaml`, and `main.py` only ever reads
> `config.yaml`. Nothing about the live scan changes. This is an easy mistake
> to make since both files are plain text — the tell is that `config.yaml`
> itself is unchanged after you "edit" a filter this way.

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

These global filters apply to every active institution.

**Keyword filter for general job boards**: some sources (currently Waltham
Forest, University of Cambridge, King's College London) are general job
boards, not culture-sector specific — most of what they post is irrelevant.
These get an *extra* filter on top of the global one: a posting only
surfaces if its title or location mentions one of a shared list of keywords
(by default: library, gallery, art, cultural, exhibitions, museum, and their
plurals). To change this:

1. In the same tool, under **Institutions**, tick/untick **"Keyword-filtered"**
   next to whichever institutions you want this applied to.
2. Edit the **"Keyword filter keywords"** field to add/remove words (comma-separated).
3. Download/copy, replace `config.yaml`, commit, push.

The keyword list and the set of institutions it applies to are both stored in
`config.yaml`'s `keyword_filter` section, and the note shown on each affected
institution's dashboard card is generated fresh from that same config every
run — so it can never drift out of sync with the actual filter.

Matching is whole-word (and whole-phrase for multi-word entries like
`project manager`), case-insensitive, and checked against the title and —
where a scraper fetches it — the job's own description text. Because it's
whole-word, plurals need their own entry: `museum` won't match "Museums", so
the list carries both `museum` and `museums` (same for `gallery`/`galleries`,
`exhibition`/`exhibitions`, and `project manager`/`project managers`). If you
add a new term and it doesn't seem to be catching postings you'd expect,
check whether you need the plural form too.

Any change here (or to the salary/employment/location/include/exclude
filters above) is retroactive: every scan re-checks every job ever recorded
in `data/seen_jobs.json` against the *current* `config.yaml`, not just newly
scraped ones — so broadening a filter can surface an older posting you'd
previously have missed, and narrowing one can drop something that used to
show. That re-check only happens during an actual scan run (the scheduled
one, or `workflow_dispatch` from the Actions tab); it doesn't update the
instant you push a config change.

**ArtsJobs UK** has its own separate, fixed filter that isn't part of the
above: it's pre-filtered to the "Museums" category at the source, via the
`ART_FORM_CATEGORY` constant near the top of `scrapers/artsjobs.py` (also used
to build both the search URL and its dashboard note).

---

## 3. Check for duplicate postings across job boards

Some sources are aggregators — general job boards that re-list postings
already sourced directly from other institutions in this project (e.g.
National Museums re-listing a National Gallery vacancy, or ArtsJobs UK
re-listing something Tate already posted directly). Anything marked as a
**job board** gets checked each run: if one of its listings has the exact
same title (case-insensitive) as a job already found from a different,
non-job-board institution that run, the job-board duplicate is dropped —
you only get notified once, from the direct source.

To mark more institutions as job boards (or unmark one):
1. Open `tools/filters-editor.html`, load your current `config.yaml`.
2. Under **Institutions**, tick/untick **"Job board"** for whichever ones apply.
3. Download/copy, replace `config.yaml`, commit, push.

This is stored in `config.yaml`'s `job_board_sources` list (currently National
Museums and ArtsJobs UK by default).

---

## 4. Change the branding (emoji, colour, opacity)

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

## 5. Add a new institution

This one needs a bit of code, since every site is structured differently. The
easiest way is to ask Claude directly: give it the vacancy-listing page URL for
the institution, and mention any special filtering you want (e.g. "add it to
the keyword filter" if it's a general job board like Cambridge/KCL/Waltham
Forest). Claude will inspect the real site, write a new file in `scrapers/`,
register it, and add a branding entry.

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

## 6. Find previous jobs in the database

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

Closing dates are always normalized to a long form with the weekday
("Sunday, 12 August 2026") regardless of how the source originally displayed
it — this happens automatically once, the first time a job is recorded.

---

## 7. Turn phone push notifications off / back on

1. Open `tools/filters-editor.html`, load your current `config.yaml`.
2. Untick **"Push notifications enabled"**.
3. Download/copy, replace `config.yaml`, commit, push.

This suppresses ntfy push without removing the feature or touching anything
else — email alerts and the dashboard keep working exactly as before. To
reactivate, tick the box again (or directly edit `config.yaml` and set
`push_notifications_enabled: true`), commit, push.
