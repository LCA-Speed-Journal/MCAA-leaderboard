# Product Requirements Document: Conference Leaderboard (MVP)

## 1. Product Overview

| | |
|--|--|
| **Name** | MCAA Conference Leaderboard |
| **Tagline** | Conference-level track & field standings and benchmarks in one place. |
| **Goal** | Replace manual pre–conference-meet spreadsheets and give coaches and athletes a single source for conference rankings and benchmark proximity (section qual, state qual, conference-podium average). |
| **Timeline** | ~8 weeks — ideally live by week of first meet; must be before conference meet. |

**Reference:** Built from research in `docs/research-ConferenceLeaderboard.txt` (market, scraping, storage, free-tier stack).

---

## 2. Target Users

### Primary: Coaches
- **Pain points:** No conference-level view on athletic.net; MileSplit paywalled; building manual spreadsheets before conference meet is time-consuming.
- **Needs:** In-depth view of how the team stacks up by event; depth of talent across the conference; who to watch at conference meet; data to roster the conference meet confidently.

### Secondary: Athletes
- **Pain points:** Don’t know where they stand in the conference; section leaderboard is the only free reference.
- **Needs:** See conference rank; see how close they are to a higher rank; see distance to section qual, state qual, and conference-podium average.

---

## 3. Problem Statement

Athletic.net can show leaderboards down to the sectional level but not at conference level. Coaches who want conference-specific analysis must manually filter and compile data or build spreadsheets before the conference meet. Athletes have no simple way to see their conference standing or proximity to key benchmarks. A free, conference-scoped tool that aggregates Team Summary data from known conference schools and presents per-event leaderboards (by PR or by average of last 3) with configurable benchmarks would solve this.

---

## 4. User Journey

- **Arrives because:** Coach or athlete needs conference-level standings; they’re told about the app or find it via team/school.
- **First sees:** A clear way to pick season, gender (men’s/women’s), and event; then a leaderboard for that event.
- **Core action:** Browse events, switch between “by PR” and “by average of last 3,” and see where our team and individual athletes sit relative to the conference and to section/state/conference-podium benchmarks.
- **Value received:** Coaches use it for rostering and scouting; athletes see their rank and how close they are to benchmarks. No more manual spreadsheet before the conference meet.

---

## 5. MVP Features

### Must-have (v1)

| # | Feature | What it does | Why essential |
|--|--------|---------------|----------------|
| 1 | **Conference config** | List of conference schools (athletic.net team IDs + names); used by scraper and shown in UI where relevant. | Defines scope of “conference”; needed for scraping and display. |
| 2 | **Scraper + storage** | Fetches athletic.net Team Summary (men’s + women’s) per school; parses athletes, events, marks, grade, gender; stores in DB; runs 2–3x per week (e.g. Mon/Wed/Fri). | Source of truth for all leaderboards and benchmarks. |
| 3 | **Leaderboard UI** | Per-event leaderboards, split men’s/women’s; toggle view by **PR** (best mark in season) or by **average of last 3** (three most recent marks). | Core value: see conference standings the way coaches and athletes need. |
| 4 | **Benchmarks** | Configurable marks per event: section qual, state qual, conference-podium average. Shown alongside rankings (e.g. as reference lines or columns) so athletes see distance to each. | Answers “how close am I?” for section, state, and podium. |

**User stories**
- As a **coach**, I want to see conference leaderboards by event and by PR or average so that I can roster the conference meet and understand depth.
- As a **coach**, I want to see section/state/conference-podium benchmarks next to rankings so that I can discuss goals with athletes.
- As an **athlete**, I want to see my conference rank and my distance to section qual, state qual, and conference-podium average so that I know where I stand and what to chase.

**Success criteria**
- Scraper runs 2–3x per week without errors; data is deduplicated and stored so PR and “avg of last 3” can be computed.
- Leaderboard loads for each event (men’s/women’s) and correctly shows PR and average-of-last-3 views.
- Benchmark values are configurable and visible next to rankings.

---

## 6. Success Metrics

- **Short term (by launch / first month):** Coaches use the app to inform conference-meet rostering; at least one coach and several athletes use it in the week before the conference meet.
- **Medium term (by 3 months):** Coaches and athletes report it’s “useful” (e.g. in conversation or simple feedback); no reversion to manual spreadsheets for conference scouting.

---

## 7. Design Direction

- **Visual style:** Clean, readable, data-first (tables/lists); trust-building for coaches and athletes. Optional: light school/team branding.
- **Key screens:** (1) Event/gender selection or overview; (2) Per-event leaderboard (rank, athlete, school, mark, PR vs avg; benchmark indicators); (3) Optional: “Our team” highlight or filter.
- **Responsive:** Usable on desktop and mobile (web only); mobile doesn’t need to be primary but must work.

---

## 8. Technical Considerations

- **Platform:** Web app; frontend responsive (desktop + mobile).
- **Data source:** athletic.net Team Summary pages (scraped responsibly: rate limits, polite delays, clear User-Agent). See research doc for details.
- **Performance:** Leaderboards should load in a few seconds; scraping runs in background 2–3x per week.
- **Security:** Scrape/refresh endpoint protected (e.g. secret token) so only your cron/scheduler can trigger it; no auth required for viewing if app is internal/school-only.
- **Stack (from research):** Scraper in Python; DB (Neon free); API + frontend (e.g. TypeScript/React on Vercel); refresh via external cron (e.g. cron-job.org) hitting your API 2–3x/week.

---

## 9. Constraints

| Constraint | Detail |
|-----------|--------|
| **Budget** | Free only — Neon free tier, Vercel Hobby, no paid scraping or DB. |
| **Timeline** | ~8 weeks; live by week of first meet; must be before conference meet. |
| **Scope** | Single conference, one season at a time; no multi-conference or multi-season comparison in v1. |
| **Data** | athletic.net only (Team Summary); confirm robots.txt and ToS. |

---

## 10. Definition of Done (Launch Checklist)

- [ ] Conference school list (athletic.net team IDs + names) configured.
- [ ] Scraper runs for all conference schools (men’s + women’s Team Summary); parses and stores athletes, events, marks, grade, gender.
- [ ] Refresh runs 2–3x per week (e.g. Mon/Wed/Fri) and completes without errors.
- [ ] Leaderboard UI: select event and gender; view by PR and by average of last 3; data matches stored data.
- [ ] Benchmarks (section qual, state qual, conference-podium average) configurable and visible per event.
- [ ] App deployed and reachable (e.g. Vercel); works on desktop and mobile.
- [ ] Coaches and athletes can use it for the week before and during conference meet.

---

**Next step:** Run `/vibe-techdesign` to create the Technical Design Document (architecture, schema, scrape pipeline, API, and frontend structure).
