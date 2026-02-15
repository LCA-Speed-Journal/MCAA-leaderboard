-- MCAA conference schools: remove placeholders and ensure all 9 are present.
-- Run this if you already ran 002_seed.sql with placeholder schools.

DELETE FROM schools
WHERE conference_id = 1 AND athletic_net_team_id LIKE 'PLACEHOLDER%';

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
ON CONFLICT (conference_id, athletic_net_team_id) DO UPDATE SET name = EXCLUDED.name;
