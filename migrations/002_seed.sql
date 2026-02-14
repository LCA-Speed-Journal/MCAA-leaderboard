-- Seed: one conference, placeholder schools, events, benchmarks
-- Run after 001_schema.sql. Replace athletic_net_team_id values with real IDs.

-- MCAA conference, 2026 season
INSERT INTO conferences (id, name, season_year) VALUES
  (1, 'MCAA', 2026)
ON CONFLICT (id) DO NOTHING;

-- Placeholder schools (replace athletic_net_team_id with real athletic.net team IDs)
INSERT INTO schools (conference_id, athletic_net_team_id, name) VALUES
  (1, 'PLACEHOLDER_1', 'School A'),
  (1, 'PLACEHOLDER_2', 'School B'),
  (1, 'PLACEHOLDER_3', 'School C')
ON CONFLICT (conference_id, athletic_net_team_id) DO NOTHING;

-- Common track & field events (slug used in API)
INSERT INTO events (name, slug, discipline, better_direction, unit) VALUES
  ('100m', '100m', 'track', 'lower', 'time'),
  ('200m', '200m', 'track', 'lower', 'time'),
  ('400m', '400m', 'track', 'lower', 'time'),
  ('800m', '800m', 'track', 'lower', 'time'),
  ('1600m', '1600m', 'track', 'lower', 'time'),
  ('3200m', '3200m', 'track', 'lower', 'time'),
  ('110m Hurdles', '110h', 'track', 'lower', 'time'),
  ('300m Hurdles', '300h', 'track', 'lower', 'time'),
  ('High Jump', 'hj', 'field', 'higher', 'distance'),
  ('Long Jump', 'lj', 'field', 'higher', 'distance'),
  ('Triple Jump', 'tj', 'field', 'higher', 'distance'),
  ('Shot Put', 'sp', 'field', 'higher', 'distance'),
  ('Discus', 'discus', 'field', 'higher', 'distance'),
  ('Pole Vault', 'pv', 'field', 'higher', 'distance')
ON CONFLICT (slug) DO NOTHING;

-- Benchmarks: optional placeholder values (NULL = not set)
-- Times in seconds; distances in meters. Update with real section/state/podium values.
INSERT INTO benchmarks (event_id, section_qual, state_qual, conference_podium_avg)
SELECT id, NULL, NULL, NULL FROM events
ON CONFLICT (event_id) DO NOTHING;
