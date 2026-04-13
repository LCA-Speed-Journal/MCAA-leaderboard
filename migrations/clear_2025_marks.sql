-- =============================================================================
-- clear_2025_marks.sql — remove prior-season dated performances
-- =============================================================================
-- Marks table has no "season" column; we use meet date. This deletes every mark
-- whose meet date is before the 2026 calendar year (removes typical 2025 outdoor
-- and any older dated rows).
--
-- Rows with mark_date IS NULL are NOT deleted (see optional block below).
--
-- Run (from project root, Neon / psql):
--   psql "%DATABASE_URL%" -v ON_ERROR_STOP=1 -f migrations/clear_2025_marks.sql
--
-- Then run scraping: python scraper/sync_conference.py --year 2026
-- =============================================================================

BEGIN;

DELETE FROM marks
WHERE mark_date IS NOT NULL
  AND mark_date < DATE '2026-01-01';

-- Optional: also remove undated marks if you are doing a full rescrape anyway
-- (uncomment only if you intend to reload everything from athletic.net)
-- DELETE FROM marks WHERE mark_date IS NULL;

COMMIT;
