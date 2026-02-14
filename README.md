# Conference Track & Field Leaderboard

Web app to analyze conference-level competition marks: aggregate data from athletic.net Team Summary pages for known conference schools, show per-event leaderboards (men's/women's) by PR or average of last 3, with benchmarks (section qual, state qual, conference-podium average).

**Status:** Phase 1 foundation in place. Next: scraper, leaderboard API, UI.

## Setup

1. `npm install`
2. Copy `.env.example` to `.env` and set `DATABASE_URL` (Neon) and `REFRESH_SECRET`.
3. Run migrations on Neon (e.g. `psql "$DATABASE_URL" -f migrations/001_schema.sql` then `002_seed.sql`).
4. `npm run dev` — frontend and API at http://localhost:3000.

## Commands

- `npm run dev` — Start dev server (Next.js + Turbopack)
- `npm run build` — Production build
- `npm run lint` — ESLint
