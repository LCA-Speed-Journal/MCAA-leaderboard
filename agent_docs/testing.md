# Testing Strategy - Conference Leaderboard MVP

## Goals
- Scraper parsing correct against sample or saved HTML.
- API returns correct leaderboard and respects query params.
- Critical paths (scrape → store → read leaderboard) verified before launch.

## Tools
- **Frontend/API:** Jest or Vitest (if Vite); test API routes with mocked DB or test DB.
- **Scraper:** Pytest; fixtures with sample HTML from athletic.net Team Summary; assert parsed athletes/events/marks.
- **E2E (optional for MVP):** Playwright or Cypress for “select event → see table” if time allows.

## What to Test
- **Scraper:** Parse one school’s Team Summary HTML → expected list of athletes/marks; normalize event names; handle missing fields.
- **API:** GET /api/leaderboard with event, gender, mode → status 200, body shape (e.g. rank, athlete, school, mark); 401 for /api/refresh without valid secret.
- **DB:** Migrations apply cleanly; unique constraints prevent duplicate marks.

## Verification Loop
1. After scraper changes: run scraper against sample HTML; assert output.
2. After API changes: run tests or manual curl; confirm response shape.
3. After schema changes: run migrations on a copy or test DB; run app and hit leaderboard.

## Pre-commit / CI (when added)
- Lint (ESLint, Ruff or Black for Python).
- Unit tests for scraper and API.
- No commit of secrets (REFRESH_SECRET, DATABASE_URL); use env or .env.example only.
