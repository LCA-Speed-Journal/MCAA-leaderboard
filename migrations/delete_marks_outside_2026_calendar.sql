-- One-shot cleanup: remove any mark whose meet date is not in calendar year 2026.
-- Matches API + scraper filter (lib/leaderboardSeason.ts, scraper/run.py).
--
--   psql "%DATABASE_URL%" -v ON_ERROR_STOP=1 -f migrations/delete_marks_outside_2026_calendar.sql

BEGIN;

DELETE FROM marks
WHERE mark_date IS NULL
   OR mark_date < DATE '2026-01-01'
   OR mark_date >= DATE '2027-01-01';

DELETE FROM athletes a
WHERE NOT EXISTS (SELECT 1 FROM marks m WHERE m.athlete_id = a.id);

COMMIT;
