# Code Patterns - Conference Leaderboard MVP

## Naming Conventions
- **DB tables:** lowercase, plural (`schools`, `athletes`, `marks`, `events`, `benchmarks`, `scrape_runs`, `conferences`).
- **API routes:** kebab-case in URL; query params lowercase (`event`, `gender`, `mode`).
- **React components:** PascalCase; files match component name.
- **Python scraper:** snake_case; modules under `scraper/` or `scripts/`.

## File Structure
```
conference-leaderboard/
├── docs/                    # PRD, TechDesign, research
├── agent_docs/              # Agent context (this folder)
├── src/ or app/             # Frontend (Vite/Next)
├── api/ or pages/api/       # API routes
├── scraper/ or scripts/     # Python scraper
├── migrations/ or sql/      # DB migrations (if used)
├── AGENTS.md
└── .cursorrules
```

## Error Handling
- **API:** Return appropriate HTTP status (400 for bad params, 401 for invalid refresh secret, 500 for server errors); JSON body with `error` or `message` when useful.
- **Scraper:** Try/except per school; log errors; update `scrape_runs` with status and optional `error_message`; exponential backoff on HTTP errors.
- **Frontend:** Show user-friendly messages for failed fetches; avoid exposing internals.

## Scraper Specifics
- Defensive parsing: check for missing elements; normalize event names to match `events` table.
- Dedupe marks: use UNIQUE (athlete_id, event_id, mark_date, value) or equivalent upsert logic.
- Never hit athletic.net without rate limiting and a clear, polite User-Agent.

## Database
- Use parameterized queries only; no string-concatenated SQL.
- Prefer one migration file per logical change; document in migration name.

## UI
- Tables: semantic `<table>`; responsive with `overflow-x: auto` on small screens.
- Sort direction: lower-is-better (times) ascending; higher-is-better (distances) descending.
- Benchmarks: show as reference row or column; optional “distance to” per athlete.
