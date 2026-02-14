# Product Requirements Summary - Conference Leaderboard MVP

**Source:** `docs/PRD-ConferenceLeaderboard-MVP.md`

## Product
- **Name:** MCAA Conference Leaderboard  
- **Tagline:** Conference-level track & field standings and benchmarks in one place.  
- **Goal:** Replace manual pre–conference-meet spreadsheets; single source for conference rankings and benchmark proximity.

## Users
- **Primary:** Coaches — need conference view by event, depth, who to watch, data to roster conference meet.
- **Secondary:** Athletes — need conference rank and distance to section qual, state qual, conference-podium average.

## Must-Have Features (v1)
1. **Conference config** — List of conference schools (athletic.net team IDs + names); used by scraper and UI.
2. **Scraper + storage** — Fetch Team Summary (men’s + women’s) per school; parse athletes, events, marks, grade, gender; store in DB; run 2–3x/week (e.g. Mon/Wed/Fri).
3. **Leaderboard UI** — Per-event leaderboards, men’s/women’s; toggle by **PR** or by **average of last 3**.
4. **Benchmarks** — Configurable per event: section qual, state qual, conference-podium average; shown alongside rankings.

## User Stories
- As a **coach**, I want to see conference leaderboards by event and by PR or average so that I can roster the conference meet and understand depth.
- As a **coach**, I want to see section/state/conference-podium benchmarks next to rankings so that I can discuss goals with athletes.
- As an **athlete**, I want to see my conference rank and distance to section qual, state qual, and conference-podium average.

## Success Criteria
- Scraper runs 2–3x per week without errors; data deduplicated; PR and avg-of-last-3 computable.
- Leaderboard loads for each event (men’s/women’s) with correct PR and average-of-last-3 views.
- Benchmark values configurable and visible next to rankings.

## Out of Scope (v1)
- Multi-conference or multi-season comparison.
- Auth (app open to anyone with link; internal/school use acceptable).
- MileSplit or sources other than athletic.net Team Summary.

## Timeline & Constraints
- ~8 weeks; live by week of first meet; must be before conference meet.
- Budget: free only. Scope: single conference, one season.
