-- Drop performances from calendar dates before the 2026 season year (removes prior outdoor / historical meets).
-- Leaderboard queries all marks; old rows otherwise keep showing as PRs.
--
-- Run from project root:
--   psql "%DATABASE_URL%" -f migrations/006_delete_marks_before_2026.sql
-- Or: python scraper/clear_marks_before_year.py
--
-- Afterward, reload current season data:
--   python scraper/sync_conference.py --year 2026

BEGIN;

DELETE FROM marks
WHERE mark_date IS NOT NULL
  AND mark_date < DATE '2026-01-01';

DELETE FROM athletes a
WHERE NOT EXISTS (SELECT 1 FROM marks m WHERE m.athlete_id = a.id);

COMMIT;
