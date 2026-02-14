# Project Brief - Conference Leaderboard MVP

## Product Vision
Single source for conference-level track & field rankings and benchmarks. Coaches stop maintaining manual spreadsheets before the conference meet; athletes see conference rank and distance to section qual, state qual, and conference-podium average.

## Conventions
- One conference, one season in v1; no multi-conference or multi-season comparison.
- Free tier only: Neon, Vercel Hobby, no paid scraping or DB.
- Data source: athletic.net Team Summary only; scrape responsibly (rate limit, User-Agent, confirm robots.txt/ToS).

## Quality Gates
- Scraper runs 2–3x per week without errors; data deduplicated.
- Leaderboard loads per event (men’s/women’s) with PR and avg-of-last-3 views correct.
- Benchmarks configurable and visible next to rankings.
- No schema changes without migration/backup plan.

## Key Commands
- `npm run dev` — Start frontend (and API if Next.js).
- `npm run build` — Production build.
- `npm test` — Run tests (when added).
- `npm run lint` — Lint (when configured).
- Scraper: run from project root with `DATABASE_URL` set (e.g. `python scraper/run.py` or similar).

## Success (from PRD)
- Coaches use app for conference-meet rostering; athletes use it for rank and benchmarks.
- No reversion to manual spreadsheets for conference scouting.
