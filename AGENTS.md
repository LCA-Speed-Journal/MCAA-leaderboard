# AGENTS.md - Master Plan for MCAA Conference Leaderboard

## Project Overview
**App:** MCAA Conference Leaderboard  
**Goal:** Conference-level track & field standings and benchmarks in one place — replace manual pre-conference spreadsheets for coaches and athletes.  
**Stack:** TypeScript/React (Vite or Next.js) on Vercel, PostgreSQL (Neon), Python scraper (BeautifulSoup + requests), external cron (cron-job.org)  
**Current Phase:** Phase 2 done; Phase 3 (Refresh & Polish) next

## How I Should Think
1. **Understand Intent First**: Identify what the user actually needs (scrape vs UI vs config).
2. **Ask If Unsure**: If critical info is missing (e.g. conference school IDs, benchmark values), ask before proceeding.
3. **Plan Before Coding**: Propose a plan, get approval, then implement.
4. **Verify After Changes**: Run tests/checks after each change; validate scraper against sample HTML.
5. **Explain Trade-offs**: When recommending (e.g. materialized view vs API-side compute), mention alternatives.

## Plan -> Execute -> Verify
1. **Plan:** Outline approach, ask for approval.
2. **Execute:** One feature at a time (e.g. schema → scraper → API → UI).
3. **Verify:** Run tests/checks, fix before moving on.

## Context Files
Load only when needed:
- `agent_docs/tech_stack.md` - Tech details, versions, setup.
- `agent_docs/code_patterns.md` - Code style, naming, error handling.
- `agent_docs/project_brief.md` - Project rules, quality gates, commands.
- `agent_docs/product_requirements.md` - Requirements, user stories, success criteria.
- `agent_docs/testing.md` - Test strategy, verification loop.

## Current State
**Last Updated:** 2026-02-13  
**Working On:** Phase 3 (refresh endpoint, error handling, mobile polish)  
**Recently Completed:** Leaderboard visualization verified with Liberty subset; table row keys hardened (rank+name+school+value+index); empty-state copy clarified; `npm run build` passes  
**Blocked By:** None  

## Roadmap

### Phase 1: Foundation
- [x] Initialize project (Next.js + Tailwind, repo structure).
- [x] Setup Neon PostgreSQL; run schema migrations (conferences, schools, athletes, events, marks, benchmarks, scrape_runs).
- [x] Seed conference and schools (athletic.net team IDs + names); seed events and benchmarks config.

### Phase 2: Core Features
- [x] Conference config: schools table + seed data (optional UI skipped for v1).
- [x] Scraper + storage: Python scraper in `/scraper`; rate limit 12 s; scrape_runs; parse_team_summary supports athletic.net Angular layout (div.athlete + event-header + table per event). Use fetch_rendered_html.py then load_fixture.py to populate DB (requests gets shell only).
- [x] Leaderboard API: GET /api/leaderboard (event, gender, mode=pr|avg3); GET /api/events; GET /api/benchmarks.
- [x] Leaderboard UI: event/gender selector; table (rank, athlete, school, mark); toggle PR vs avg of last 3.
- [x] Benchmarks: configurable per event; show alongside leaderboard.
- [x] POST /api/refresh (Bearer REFRESH_SECRET); MVP returns OK (run scraper externally).

### Phase 3: Refresh & Polish
- [ ] Refresh endpoint: POST /api/refresh with Authorization: Bearer REFRESH_SECRET; invoke scraper; wire cron-job.org 2–3x/week.
- [ ] Error handling and scraper resilience (exponential backoff, defensive parsing).
- [ ] Mobile responsiveness (tables overflow-x, tap-friendly).

### Phase 4: Launch
- [ ] Deploy to Vercel; env (DATABASE_URL, REFRESH_SECRET).
- [ ] Verify scraper runs 2–3x/week; leaderboards load; benchmarks visible.
- [ ] Launch checklist (PRD Section 10) complete.

## What NOT To Do
- Do NOT delete files without confirmation.
- Do NOT modify database schemas without a backup/migration plan.
- Do NOT add features not in current phase (e.g. multi-conference, auth in v1).
- Do NOT skip tests for "simple" changes (especially scraper parsing).
- Do NOT use deprecated libraries; stick to stack in Tech Design.
- Do NOT scrape without rate limiting (10–15 s between school requests) or clear User-Agent.
