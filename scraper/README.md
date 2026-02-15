# Scraper

Fetches athletic.net Team Summary pages and parses athletes/marks into the DB.

## Setup

From the **conference-leaderboard** project root:

```bash
pip install -r scraper/requirements.txt
# If using fetch_rendered_html.py (to capture JS-rendered content):
playwright install chromium
```

## Parser

- **`parse_team_summary(html, school_id, gender)`** in `run.py` parses Team Summary HTML.
- If the HTML is the Angular shell only (no `<table>` with `<tbody><tr>...</tr></tbody>`), it returns `[]`.
- Otherwise it finds a table with `<thead>` and `<tbody>`, maps header cells to event slugs (100m, 200m, 110h, hj, etc.), and extracts per-row: athlete name, grade, and mark values (times in seconds, distances in meters).

### Test on a saved HTML file

```bash
cd conference-leaderboard
python scraper/parse_sample.py "path/to/team-summary.html"
```

Without arguments it looks for `scraper/fixtures/team_summary_73442_2025.html`.

### Get rendered HTML (optional)

The live team summary page is built by Angular and has **Men** / **Women** / **Relays** tabs (default Men). To get the full table:

1. **Men only:** `python scraper/fetch_rendered_html.py 73442 2025`  
   Saves `team_summary_73442_2025.html`
2. **Women only:** `python scraper/fetch_rendered_html.py 73442 2025 women`  
   Saves `team_summary_73442_2025_women.html`
3. **Relays only:** `python scraper/fetch_rendered_html.py 73442 2025 relays`  
   Saves `team_summary_73442_2025_relays.html` (men’s and women’s relays together on one tab).
4. **All three:** `python scraper/fetch_rendered_html.py 73442 2025 all`  
   Saves men, women, and relays in one run.

Then run `python scraper/parse_sample.py [path]` to test the parser, or use `load_fixture.py` to push into the DB.

**Relays:** The Relays tab shows men’s and women’s relays together. The parser supports the Relays tab layout: run `load_fixture.py` on the relays file twice (once with `men`, once with `women`) so both Men's and Women's relay marks are stored. Each participating athlete gets the relay mark so the leaderboard can show the team's best 4x100, 4x200, etc.

## Load a fixture into the DB

After saving rendered HTML with `fetch_rendered_html.py`:

```bash
# From project root, with DATABASE_URL set
python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025.html 1 men
python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025_women.html 1 women
```

To include relay marks (4x100, 4x200, 4x400, 4x800), fetch the Relays tab and load it for both genders:

```bash
python scraper/fetch_rendered_html.py 73442 2025 relays
python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025_relays.html 1 men
python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025_relays.html 1 women
```

Use the `school_id` from your `schools` table (e.g. 1 for Liberty Classical Academy).

## One-command sync per school (recommended)

To fetch men, women, and relays for one school and load all marks in a single run:

```bash
# From project root, DATABASE_URL set; requires Playwright
python scraper/sync_school.py <team_id> <school_id> [--year YEAR]
```

Example (Liberty Classical Academy, athletic.net team 73442, school_id 1):

```bash
python scraper/sync_school.py 73442 1
python scraper/sync_school.py 73442 1 --year 2025
```

This opens one browser session, fetches all three tabs (men, women, relays), writes the same three HTML files to `scraper/fixtures/`, then parses and upserts all four datasets (men, women, relays-men, relays-women) with one DB connection. Use `--no-save-fixtures` to skip writing HTML files.

## Reset athletes and marks (fresh IDs)

To clear all athletes and marks and reset IDs before re-running the scraper:

```bash
psql $DATABASE_URL -f migrations/003_reset_athletes_marks.sql
```

This truncates `marks` and `athletes` and restarts their sequences. Conferences, schools, events, and benchmarks are left unchanged.

## Full scrape (with DB)

`python scraper/run.py` uses `requests` only; athletic.net returns the Angular shell, so no athlete data is parsed. To populate from live data, use `fetch_rendered_html.py` for each school/year/gender (or run Playwright inside the scraper). Then use `load_fixture.py` to push saved HTML into the DB. Rate limit: 12 s between school requests when fetching.
