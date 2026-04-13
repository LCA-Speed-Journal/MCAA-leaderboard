-- =============================================================================
-- clear_2025_athletes.sql — remove athlete rows so a rescrape can rebuild rosters
-- =============================================================================
-- The athletes table has NO season/year column. "Clearing 2025 athletes" means
-- either:
--
--   A) Delete everyone in your conference (full reset; CASCADE deletes their marks)
--   B) After deleting old marks, delete athletes who have zero marks left (orphans)
--
-- Pick ONE of the blocks below (not both). Default below is (A) for MCAA (conference_id = 1).
--
-- Run AFTER clear_2025_marks.sql if you use (B), or run (A) alone (it removes marks too).
--
--   psql "%DATABASE_URL%" -v ON_ERROR_STOP=1 -f migrations/clear_2025_athletes.sql
--
-- Then: python scraper/sync_conference.py --year 2026
-- =============================================================================

BEGIN;

-- ----- Option A: all athletes in one conference (recommended full refresh) -----
-- Adjust conference_id if yours is not 1.
DELETE FROM athletes AS a
  USING schools AS s
 WHERE a.school_id = s.id
   AND s.conference_id = 1;

-- ----- Option B: only athletes with no marks (use if you already ran clear_2025_marks.sql
--       and want to keep athletes who still have 2026-dated marks) -----
-- DELETE FROM athletes AS a
--  WHERE NOT EXISTS (
--    SELECT 1 FROM marks AS m WHERE m.athlete_id = a.id
--  );

COMMIT;
