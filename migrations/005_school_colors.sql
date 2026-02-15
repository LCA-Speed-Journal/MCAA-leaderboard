-- Add school colors for UI (left accent, school name color)
ALTER TABLE schools ADD COLUMN IF NOT EXISTS primary_color TEXT;
ALTER TABLE schools ADD COLUMN IF NOT EXISTS secondary_color TEXT;

-- Seed MCAA schools with distinct hex colors (conference_id = 1)
UPDATE schools SET primary_color = '#1E40AF', secondary_color = '#3B82F6' WHERE name = 'Liberty Classical Academy' AND conference_id = 1;
UPDATE schools SET primary_color = '#047857', secondary_color = '#10B981' WHERE name = 'Eagle Ridge Academy' AND conference_id = 1;
UPDATE schools SET primary_color = '#7C2D12', secondary_color = '#B45309' WHERE name = 'Christ''s Household of Faith' AND conference_id = 1;
UPDATE schools SET primary_color = '#4C1D95', secondary_color = '#7C3AED' WHERE name = 'Math & Science Academy' AND conference_id = 1;
UPDATE schools SET primary_color = '#0F766E', secondary_color = '#14B8A6' WHERE name = 'Mayer Lutheran' AND conference_id = 1;
UPDATE schools SET primary_color = '#BE185D', secondary_color = '#EC4899' WHERE name = 'NLA/LILA' AND conference_id = 1;
UPDATE schools SET primary_color = '#B45309', secondary_color = '#F59E0B' WHERE name = 'Parnassus Preparatory Academy' AND conference_id = 1;
UPDATE schools SET primary_color = '#0369A1', secondary_color = '#0EA5E9' WHERE name = 'Spectrum High School' AND conference_id = 1;
UPDATE schools SET primary_color = '#6D28D9', secondary_color = '#8B5CF6' WHERE name = 'West Lutheran' AND conference_id = 1;
