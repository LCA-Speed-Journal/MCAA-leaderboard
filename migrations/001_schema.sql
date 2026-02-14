-- Conference Leaderboard MVP - initial schema
-- Run against Neon PostgreSQL (e.g. psql $DATABASE_URL -f migrations/001_schema.sql)

-- Conferences (one per season for MVP)
CREATE TABLE IF NOT EXISTS conferences (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  season_year INTEGER NOT NULL
);

-- Schools in the conference (athletic.net team IDs)
CREATE TABLE IF NOT EXISTS schools (
  id SERIAL PRIMARY KEY,
  conference_id INTEGER NOT NULL REFERENCES conferences(id) ON DELETE CASCADE,
  athletic_net_team_id TEXT NOT NULL,
  name TEXT NOT NULL,
  UNIQUE(conference_id, athletic_net_team_id)
);

-- Athletes per school
CREATE TABLE IF NOT EXISTS athletes (
  id SERIAL PRIMARY KEY,
  school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  grade INTEGER,
  gender CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
  athletic_net_id TEXT,
  UNIQUE(school_id, name, grade, gender)
);

-- Events (track/field; used for leaderboard and benchmarks)
CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  discipline TEXT NOT NULL CHECK (discipline IN ('track', 'field')),
  better_direction TEXT NOT NULL CHECK (better_direction IN ('lower', 'higher')),
  unit TEXT NOT NULL CHECK (unit IN ('time', 'distance'))
);

-- Marks (one row per performance)
CREATE TABLE IF NOT EXISTS marks (
  id SERIAL PRIMARY KEY,
  athlete_id INTEGER NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  value NUMERIC NOT NULL,
  mark_date DATE,
  meet_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(athlete_id, event_id, mark_date, value)
);

CREATE INDEX IF NOT EXISTS idx_marks_athlete_event ON marks(athlete_id, event_id);
CREATE INDEX IF NOT EXISTS idx_marks_event ON marks(event_id);

-- Benchmarks per event (section qual, state qual, conference-podium avg)
CREATE TABLE IF NOT EXISTS benchmarks (
  event_id INTEGER NOT NULL PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  section_qual NUMERIC,
  state_qual NUMERIC,
  conference_podium_avg NUMERIC
);

-- Scrape run metadata
CREATE TABLE IF NOT EXISTS scrape_runs (
  id SERIAL PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
  schools_processed INTEGER DEFAULT 0,
  error_message TEXT
);
