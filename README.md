# Conference Track & Field Leaderboard

Web app to analyze conference-level competition marks: aggregate data from athletic.net Team Summary pages for known conference schools, show per-event leaderboards (men's/women's) by PR or average of last 3, with benchmarks (section qual, state qual, conference-podium average).

**Status:** Parser works on athletic.net full-season HTML. Next: add your school to DB, load fixture, run leaderboard.

## Setup

1. `npm install`
2. Copy `.env.example` to `.env` and set `DATABASE_URL` (Neon) and `REFRESH_SECRET`.
3. Run migrations on Neon (e.g. `psql "$DATABASE_URL" -f migrations/001_schema.sql` then `002_seed.sql`).
4. `npm run dev` — frontend and API at http://localhost:3000.

## Commands

- `npm run dev` — Start dev server (Next.js + Turbopack)
- `npm run build` — Production build
- `npm run lint` — ESLint

## Loading team data (scraper)

Athletic.net’s team summary is JS-rendered, so:

1. **Fetch rendered HTML** (once per team/year; page has Men / Women / Relays tabs):  
   `python scraper/fetch_rendered_html.py <team_id> <year> [view]`  
   Examples:  
   - Men: `python scraper/fetch_rendered_html.py 73442 2025` → `team_summary_73442_2025.html`  
   - Women: `python scraper/fetch_rendered_html.py 73442 2025 women` → `team_summary_73442_2025_women.html`  
   - Relays: `python scraper/fetch_rendered_html.py 73442 2025 relays` → `team_summary_73442_2025_relays.html`  
   - All: `python scraper/fetch_rendered_html.py 73442 2025 all`

2. **Add the school in the DB** if needed (e.g. in Neon SQL):  
   `INSERT INTO schools (conference_id, athletic_net_team_id, name) VALUES (1, '73442', 'Liberty Classical Academy') ON CONFLICT (conference_id, athletic_net_team_id) DO NOTHING;`

3. **Load HTML into the DB** (when using pre-saved fixtures; run once per gender):  
   `python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025.html 1 men`  
   `python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025_women.html 1 women`  
   Use the correct `school_id` from your `schools` table.

4. **One school (fetch + load in one go):**  
   `python scraper/sync_school.py <team_id> <school_id> [--year 2025]`  
   Example: `python scraper/sync_school.py 73442 1`  
   Uses Playwright to fetch Men, Women, and Relays, then parses and upserts. Optional `--no-save-fixtures` to skip writing HTML files.

5. **All schools in the conference:**  
   `python scraper/sync_conference.py [--year 2025] [--conference-id 1]`  
   Reads schools from the DB (skips rows where `athletic_net_team_id` starts with `PLACEHOLDER`), then for each school runs the same fetch+parse+upsert as sync_school. Waits 12s between schools. Add real athletic.net team IDs to your `schools` table first, then run this once to scrape every team.
