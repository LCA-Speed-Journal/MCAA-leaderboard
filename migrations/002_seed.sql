-- Seed: one conference, placeholder schools, events, benchmarks
-- Run after 001_schema.sql. Replace athletic_net_team_id values with real IDs.

-- MCAA conference, 2026 season
INSERT INTO conferences (id, name, season_year) VALUES
  (1, 'MCAA', 2026)
ON CONFLICT (id) DO NOTHING;

-- MCAA conference schools (athletic.net team IDs)
INSERT INTO schools (conference_id, athletic_net_team_id, name) VALUES
  (1, '73442', 'Liberty Classical Academy'),
  (1, '12529', 'Eagle Ridge Academy'),
  (1, '12207', 'Christ''s Household of Faith'),
  (1, '12079', 'Math & Science Academy'),
  (1, '12454', 'Mayer Lutheran'),
  (1, '34824', 'NLA/LILA'),
  (1, '75792', 'Parnassus Preparatory Academy'),
  (1, '38174', 'Spectrum High School'),
  (1, '12356', 'West Lutheran')
ON CONFLICT (conference_id, athletic_net_team_id) DO NOTHING;

-- Events: finalized list (matches production; ids may differ on fresh install)
INSERT INTO events (name, slug, discipline, better_direction, unit) VALUES
  ('100m', '100m', 'track', 'lower', 'time'),
  ('200m', '200m', 'track', 'lower', 'time'),
  ('400m', '400m', 'track', 'lower', 'time'),
  ('800m', '800m', 'track', 'lower', 'time'),
  ('1600m', '1600m', 'track', 'lower', 'time'),
  ('3200m', '3200m', 'track', 'lower', 'time'),
  ('110m Hurdles', '110h', 'track', 'lower', 'time'),
  ('100m Hurdles', '100h', 'track', 'lower', 'time'),
  ('300m Hurdles', '300h', 'track', 'lower', 'time'),
  ('4x100m Relay', '4x100', 'track', 'lower', 'time'),
  ('4x200m Relay', '4x200', 'track', 'lower', 'time'),
  ('4x400m Relay', '4x400', 'track', 'lower', 'time'),
  ('High Jump', 'hj', 'field', 'higher', 'distance'),
  ('Long Jump', 'lj', 'field', 'higher', 'distance'),
  ('Triple Jump', 'tj', 'field', 'higher', 'distance'),
  ('Shot Put', 'sp', 'field', 'higher', 'distance'),
  ('Discus', 'discus', 'field', 'higher', 'distance'),
  ('Pole Vault', 'pv', 'field', 'higher', 'distance'),
  ('60m Hurdles', '60h', 'track', 'lower', 'time'),
  ('4x800m Relay', '4x800', 'track', 'lower', 'time')
ON CONFLICT (slug) DO NOTHING;

-- Benchmarks: optional placeholder values (NULL = not set)
-- Times in seconds; distances in meters. Update with real section/state/podium values.
INSERT INTO benchmarks (event_id, section_qual, state_qual, conference_podium_avg)
SELECT id, NULL, NULL, NULL FROM events
ON CONFLICT (event_id) DO NOTHING;
