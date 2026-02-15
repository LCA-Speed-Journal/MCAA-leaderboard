-- Reset athletes and marks for a fresh scrape (IDs start from 1 again).
-- Run when re-testing the scraper: psql $DATABASE_URL -f migrations/003_reset_athletes_marks.sql
-- Leaves conferences, schools, events, benchmarks, and scrape_runs unchanged.

TRUNCATE marks, athletes RESTART IDENTITY;
