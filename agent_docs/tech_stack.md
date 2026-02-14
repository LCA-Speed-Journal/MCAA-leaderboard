# Tech Stack - Conference Leaderboard MVP

## Overview
| Layer | Choice | Notes |
|-------|--------|--------|
| Frontend | TypeScript + React (Vite or Next.js) | Vercel deploy; responsive, free Hobby tier. |
| API | Next.js API routes or Vercel serverless (Node) | Serves leaderboard and config; can invoke or proxy to scraper. |
| Database | Neon PostgreSQL (free) | Serverless Postgres; use connection string in env. |
| Scraper | Python 3.x (BeautifulSoup4 + requests) | In `/scraper` or `/scripts`; rate limit, clear User-Agent. |
| Refresh | External cron (e.g. cron-job.org) | POST to `/api/refresh` with Bearer REFRESH_SECRET 2–3x/week. |

## Frontend
- **React** + **TypeScript**
- **Vite** or **Next.js** (e.g. `npm create vite@latest . -- --template react-ts` or `npx create-next-app`)
- **Tailwind CSS** (or plain CSS) for layout and tables
- Build: `npm run build`; dev: `npm run dev`

## API (Node)
- **Next.js API routes** or Vercel serverless
- DB client: `@neondatabase/serverless` or `pg` for Neon
- Routes:
  - `GET /api/leaderboard?event=X&gender=men|women&mode=pr|avg3`
  - `POST /api/refresh` (header: `Authorization: Bearer <REFRESH_SECRET>`)

## Database (Neon)
- **PostgreSQL** via Neon free tier
- Connection: `DATABASE_URL` (from Neon dashboard)
- Run migrations for schema (see `project_brief.md` or Tech Design Section 6)

## Scraper (Python)
- **requests** — HTTP with rate limiting and backoff
- **beautifulsoup4** — HTML parsing
- **lxml** — parser (optional, faster)
- **DB driver:** `psycopg2` or Neon serverless-compatible driver; env `DATABASE_URL`
- URL pattern: `https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary`
- Rate limit: 10–15 s between school requests; User-Agent e.g. `ConferenceLeaderboard/1.0 (school use; contact email)`

## Environment Variables
- `DATABASE_URL` — Neon connection string (API + scraper)
- `REFRESH_SECRET` — Secret for POST /api/refresh (cron only)

## Deployment
- **Vercel:** Connect repo; set `DATABASE_URL`, `REFRESH_SECRET`; deploy on push.
- **Neon:** Create project; run migrations; no built-in cron — use cron-job.org.

## Version Guidance
- Use current LTS Node (e.g. 18+); Python 3.10+.
- Pin versions in `package.json` and `requirements.txt`; avoid deprecated deps.
