# Technical Design: Conference Leaderboard (MVP)

**Product:** MCAA Conference Leaderboard — conference-level track & field standings and benchmarks.  
**References:** `docs/PRD-ConferenceLeaderboard-MVP.md`, `docs/research-ConferenceLeaderboard.txt`

---

## 1. Recommended Approach

**Stack: Web app on Vercel (frontend + API) + PostgreSQL (Neon free) + Python scraper triggered 2–3x/week via external cron.**

| Layer | Choice | Why |
|-------|--------|-----|
| **Frontend** | TypeScript + React (Vite or Next.js) on Vercel | You already used TS/Vercel; responsive, free Hobby tier. |
| **API** | Next.js API routes or Vercel serverless (Node) | Serves leaderboard and config; can invoke or proxy to scraper. |
| **Database** | Neon (PostgreSQL, free) | You already have an account; free tier supports many projects; serverless Postgres, standard SQL. |
| **Scraper** | Python (BeautifulSoup + requests) | Your strength; run as script invoked by cron or by a serverless function (e.g. Vercel with Python runtime). |
| **Refresh trigger** | External cron (e.g. cron-job.org) → `POST /api/refresh` with secret header, 2–3x/week (e.g. Mon/Wed/Fri) | Neon has no built-in cron; Vercel Hobby cron is once/day only. Free external cron gives full control over schedule. |

**Flow:** (1) cron-job.org (or similar) hits a protected API route (e.g. `POST /api/refresh` with secret header) on your chosen days. (2) API runs or invokes the Python scraper; scraper fetches each conference school’s Team Summary (men’s + women’s), parses, writes to Neon. (3) Frontend reads from Neon (via API or serverless driver) and displays leaderboards + benchmarks.

**Refresh with Neon:** Because Neon doesn’t provide pg_cron, use a free external scheduler (e.g. [cron-job.org](https://cron-job.org)): create a job that runs 2–3 times per week (e.g. Mon/Wed/Fri at an off-peak time), sends `POST` to `https://your-app.vercel.app/api/refresh` with a header such as `Authorization: Bearer <REFRESH_SECRET>`. Keep `REFRESH_SECRET` in Vercel env and validate it in the refresh route so only your cron can trigger scrapes.

**Why this fits:** Free end-to-end; reuses your existing Neon account and Python/TypeScript/Vercel experience; one less new vendor; clear separation between scrape job and read-heavy UI.

---

## 2. Alternative Options

| Option | Pros | Cons |
|--------|-----|-----|
| **Supabase (Postgres) + pg_cron** | Built-in cron; one platform for DB + scheduling. | New account; free tier limited to 2 projects. |
| **Supabase only (no Vercel)** | One platform; Edge Functions for API + cron. | Edge is Deno/TS, not Python; you’d need to port scraper to TS or call out to a Python service. |
| **Full Python backend (FastAPI on Railway/Fly.io)** | Single language; scraper and API together. | Free tiers are limited; you’d still need a frontend (or serve simple HTML). Less alignment with your Vercel experience. |

**Recommendation:** Use **Neon + Vercel + cron-job.org** (or similar) for MVP: Neon for Postgres (you already have an account), external cron for 2–3x/week refresh. Supabase remains an option if you prefer built-in pg_cron and don’t mind a second DB vendor.

---

## 3. Project Setup (Step-by-Step)

1. **Repo:** Create `conference-leaderboard` (or use existing); ensure `docs/` has PRD and research.
2. **Vercel:** New project; connect repo; set env vars (e.g. `DATABASE_URL` for Neon, `REFRESH_SECRET` for the scrape endpoint).
3. **Neon:** New project in your existing account (or use a branch); note connection string. Run migrations for the schema below (Section 6).
4. **Frontend:** `npm create vite@latest . -- --template react-ts` or `npx create-next-app`; add Tailwind (or simple CSS) for layout and tables.
5. **API:** Add route for leaderboard read (e.g. `GET /api/leaderboard?event=X&gender=men&mode=pr`) and for refresh (e.g. `POST /api/refresh` with `Authorization: Bearer <REFRESH_SECRET>`).
6. **Scraper:** Python project in `/scraper` or `/scripts`: `requests`, `beautifulsoup4`, `lxml`; env for `DATABASE_URL` (Neon connection string; use serverless driver or `psycopg2`). Implement rate limiting (e.g. 10–15 s between school requests), clear User-Agent, exponential backoff.
7. **Refresh:** Use [cron-job.org](https://cron-job.org) (or similar): create a job that runs 2–3x/week (e.g. Mon/Wed/Fri), sends `POST` to `https://your-app.vercel.app/api/refresh` with header `Authorization: Bearer <REFRESH_SECRET>`.
8. **Benchmarks:** Table or config (e.g. `benchmarks` in DB or JSON in repo) with event_id, section_qual, state_qual, conference_podium_avg.

---

## 4. Feature Implementation

### 4.1 Conference config

- **Storage:** `schools` table: `id`, `athletic_net_team_id`, `name`, `conference_id` (or single conference: one row in `conferences` with id, name).
- **Seeding:** SQL insert or seed script with your conference’s athletic.net team IDs and names.
- **UI (optional for v1):** Admin or config page to list schools; or keep as DB/env only and show school names in leaderboard table.

### 4.2 Scraper + storage

- **Input:** List of (athletic_net_team_id, name); season year (e.g. 2026).
- **URL pattern:** `https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary`; one request per gender (men/women) per school, or one page that includes both if URL structure allows.
- **Parse:** BeautifulSoup; extract per-athlete rows: name, grade, event, mark, date (if present). Normalize event names to match your `events` table.
- **Rate limiting:** 10–15 s between requests; User-Agent: e.g. `ConferenceLeaderboard/1.0 (school use; contact email)`.
- **Write:** Upsert schools, athletes (by school + name + grade + gender), marks (athlete_id, event_id, value, date, meet). Dedupe on (athlete_id, event_id, date, value or meet).
- **Refresh metadata:** Table `scrape_runs`: `id`, `started_at`, `finished_at`, `status`, `schools_processed`, `error_message` (optional). Update after each run.

### 4.3 Leaderboard UI

- **Screens:** (1) Event list or dropdown + gender (Men/Women). (2) Leaderboard table: Rank, Athlete, School, Mark, and a toggle “By PR” vs “By avg of last 3”.
- **Data:** API that reads from Neon: either pre-computed views (e.g. `leaderboard_pr`, `leaderboard_avg3`) or raw marks + compute in API. Recommended: materialized view or computed table updated after each scrape (PR and avg-of-last-3 per athlete per event per gender).
- **Sorting:** For “lower is better” (times), ascending; for “higher is better” (distances), descending.

### 4.4 Benchmarks

- **Storage:** Table `benchmarks`: `event_id`, `section_qual`, `state_qual`, `conference_podium_avg` (or separate columns per benchmark type). One row per event.
- **UI:** On leaderboard screen, show these values (e.g. as reference rows or a sidebar); optionally show “distance to section qual” etc. per athlete (computed from mark − benchmark for times, or benchmark − mark for distances).

---

## 5. Design Implementation

- **Style:** Clean, table-first; sufficient contrast and font size for accessibility. Optional: light school colors or logo in header.
- **Key components:** Event/gender selector; leaderboard table (responsive: horizontal scroll on small screens if needed); PR vs Avg toggle; benchmark section or column.
- **Responsive:** Flexbox/Grid; table with `overflow-x: auto` on mobile; tap-friendly targets.
- **No design system required for MVP:** Tailwind or plain CSS; reuse patterns from your LCA-Speed app if desired.

---

## 6. Database & Storage

### 6.1 Schema (PostgreSQL)

```text
conferences     id, name, season_year
schools         id, conference_id, athletic_net_team_id, name
athletes        id, school_id, name, grade, gender (M/F), athletic_net_id (nullable)
events          id, name, slug, discipline (track/field), better_direction (lower/higher), unit (time/distance)
marks           id, athlete_id, event_id, value (numeric), mark_date, meet_name, created_at
                UNIQUE(athlete_id, event_id, mark_date, value) or similar for dedupe
benchmarks      event_id, section_qual, state_qual, conference_podium_avg
scrape_runs     id, started_at, finished_at, status, schools_processed, error_message
```

### 6.2 Derived data (PR and avg of last 3)

- **Option A (recommended):** After each scrape, compute and store in `leaderboard_pr` and `leaderboard_avg3` (e.g. athlete_id, event_id, gender, value, rank). Frontend just reads and displays.
- **Option B:** SQL view or API-side computation: PR = `MIN(value)` per athlete/event; avg of last 3 = `AVG(value)` over last 3 marks by date per athlete/event. Slightly more load on read.

### 6.3 Hosting

- **Neon (recommended):** Free tier Postgres; use for all tables. You already have an account; supports many projects. Trigger refresh via external cron (e.g. cron-job.org) calling `POST /api/refresh` with secret header 2–3x/week.
- **Supabase (alternative):** Free tier, 1 GB, 5 GB egress; built-in pg_cron if you prefer not to use an external cron service.

---

## 7. AI Assistance Strategy

- **Scraper logic and parsing:** Use AI to generate BeautifulSoup selectors and normalize event names; validate against sample HTML.
- **API and frontend:** Use AI for Next.js/React components and Neon client calls (e.g. `@neondatabase/serverless` or `pg`); you review and adjust.
- **Schema and SQL:** Use AI to draft migrations and views; run and test locally or in Neon SQL editor.
- **When stuck:** Prefer “explain and suggest” so you learn; for time-critical path (e.g. scrape reliability), ask for concrete code and tests.

---

## 8. Deployment Plan

1. **Vercel:** Connect Git repo; set env (e.g. `DATABASE_URL` from Neon, `REFRESH_SECRET`). Deploy on push.
2. **Neon:** Create project (or branch) in your account; run migrations (schema above). No built-in cron — use cron-job.org to call `POST /api/refresh` with `Authorization: Bearer <REFRESH_SECRET>` 2–3x/week.
3. **Scraper:** If Python runs on Vercel (e.g. serverless Python), ensure timeout and memory are sufficient for N schools × 2 (men/women); if not, chunk (e.g. 3 schools per invocation, multiple cron triggers) or run scraper elsewhere and have it POST to an ingest endpoint.
4. **Backup:** Neon free tier; export `schools`, `athletes`, `marks`, `events`, `benchmarks` to SQL or CSV periodically if you want a manual backup.

---

## 9. Cost Breakdown

| Phase | Cost |
|-------|------|
| **Development** | $0 (your time; free tiers only). |
| **Production (MVP)** | $0 — Vercel Hobby, Neon free, cron-job.org (or similar) free; no paid cron. |
| **If you outgrow free** | Vercel Pro if you need more functions; Neon paid if storage or compute grows. |

---

## 10. Scaling Path

- **~100 users (your conference):** Current design is sufficient; single Neon project, Vercel Hobby.
- **1K users / multiple conferences:** Add conference selector; same schema with `conference_id`; consider read replicas or caching (e.g. Vercel edge cache for leaderboard responses) if needed.
- **10K+ users:** Dedicated scrape worker; CDN for static assets; consider Neon paid or dedicated Postgres for higher connections and storage.

---

## 11. Limitations

- **Scraping:** Depends on athletic.net’s HTML structure; breakage possible if they redesign. Mitigate with defensive parsing and a small test with saved HTML.
- **Vercel serverless timeout:** Default 10 s (Hobby); scraping many schools may exceed. Use chunked runs (e.g. 2–3 schools per invocation) or move scraper to a long-running job (e.g. GitHub Actions scheduled workflow that runs Python and writes to Neon).
- **No auth in v1:** App is open to anyone with the link; acceptable for internal/school use. Add auth (e.g. NextAuth or password-protected route) if you need to restrict access later.
- **Single season:** MVP is one conference, one season; multi-season comparison is out of scope for v1.

---

**Next step:** Run `/vibe-agents` to generate AGENTS.md and AI configuration for this project, or start implementation using this design.
