# 2026 season full fixtures cutover — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all 2025 test HTML fixtures, switch CLI/parser defaults and docs to the 2026 outdoor season, regenerate the full conference fixture mirror (method A: nine teams × men/women/relays), and verify the Python scraper plus Next.js build.

**Architecture:** Treat **2026** as the default season year everywhere user-facing (`argparse` defaults, relay date fallbacks, `diagnose_parser` glob patterns). Replace `scraper/fixtures/team_summary_*_2025*.html` with freshly fetched `*_2026*.html` using `sync_conference.py` (Playwright → same filenames with new year). No schema changes. Optional: run this branch in a **git worktree** (@`.cursor/skills/using-git-worktrees/SKILL.md`) so large fixture churn does not block other work.

**Tech Stack:** Python 3 (scraper), Playwright, Neon/Postgres (`DATABASE_URL` in `.env` / `.env.local`), Next.js 14 (`npm run build`).

**Prerequisites:** `pip install playwright python-dotenv` and `python -m playwright install chromium`. Project root for all commands: `conference-leaderboard/` (the folder containing `package.json` and `scraper/`).

**Fixture scope (method A):** Current checked-in teams match `diagnose_parser.py` `TEAM_LABELS`: `73442`, `12529`, `12207`, `12079`, `12454`, `34824`, `75792`, `38174`, `12356` — **27 files** today (`*_2025.html`, `*_2025_women.html`, `*_2025_relays.html`). After cutover, the same **27 paths** with `_2026` in the name.

**Docs out of scope:** Do not edit `docs/plans/2026-02-15-leaderboard-ui-polish-*.md` — those dates are UI **examples**, not season runbooks.

---

### Task 1: Default season year — `fetch_rendered_html.py`

**Files:**
- Modify: `scraper/fetch_rendered_html.py` (docstring ~lines 9–11, `year =` ~line 56)

**Step 1:** Change every `2025` in the docstring and the default `year` assignment to `2026`.

```python
year = sys.argv[2] if len(sys.argv) > 2 else "2026"
```

**Step 2:** Commit

```bash
git add scraper/fetch_rendered_html.py
git commit -m "chore(scraper): default fetch year to 2026"
```

---

### Task 2: Default season year — `sync_school.py` and `sync_conference.py`

**Files:**
- Modify: `scraper/sync_school.py` (module docstring example ~line 11, `parser.add_argument("--year"` ~line 39)
- Modify: `scraper/sync_conference.py` (module docstring example ~line 12, `parser.add_argument("--year"` ~line 40)

**Step 1:** Set `default="2026"` and update help text to say `default: 2026`. Update docstring examples from `--year 2025` to `--year 2026`.

**Step 2:** Commit

```bash
git add scraper/sync_school.py scraper/sync_conference.py
git commit -m "chore(scraper): default sync scripts to season 2026"
```

---

### Task 3: Relay parser fallbacks — `run.py`

**Files:**
- Modify: `scraper/run.py` (~lines 273, 335–336)

**Step 1:** Update `_parse_relay_meet_date` default:

```python
def _parse_relay_meet_date(cell, default_year: int = 2026):
```

**Step 2:** Update the fallback inside `_parse_athletic_net_relays` after the heading scan fails:

```python
    # Infer season year from page (e.g. h2 "2026 Event Progress")
    default_year = 2026
```

**Step 3:** Commit

```bash
git add scraper/run.py
git commit -m "chore(scraper): relay date fallback year 2026"
```

---

### Task 4: `diagnose_parser.py` — glob and stem parsing for `_2026`

**Files:**
- Modify: `scraper/diagnose_parser.py` (~lines 48–52, 61–62, 92)

**Step 1:** Replace comments and globs:

- `team_summary_*_2025.html` → `team_summary_*_2026.html`
- `team_summary_*_2025_women.html` → `team_summary_*_2026_women.html`

**Step 2:** Replace stem cleanup:

- `.replace("_2025", "")` → `.replace("_2026", "")`
- `.replace("_2025_women", "")` → `.replace("_2026_women", "")`

**Step 3:** Commit

```bash
git add scraper/diagnose_parser.py
git commit -m "chore(scraper): diagnose_parser expects 2026 fixtures"
```

---

### Task 5: Helper scripts — docstrings and default paths

**Files:**
- Modify: `scraper/load_fixture.py` (docstring example ~line 10)
- Modify: `scraper/inspect_event_headers.py` (example ~line 7)
- Modify: `scraper/inspect_all_events.py` (default path ~line 19 — use `team_summary_12207_2026_women.html`)
- Modify: `scraper/parse_sample.py` (docstring, default path, print hint ~lines 5, 19–22)

**Step 1:** Replace every `2025` reference in those strings with `2026` (same team IDs).

**Step 2:** Commit

```bash
git add scraper/load_fixture.py scraper/inspect_event_headers.py scraper/inspect_all_events.py scraper/parse_sample.py
git commit -m "chore(scraper): update helper script examples to 2026 fixtures"
```

---

### Task 6: Documentation — root README, scraper README, debug doc

**Files:**
- Modify: `README.md` (loading team data section — all `2025` → `2026` in commands and filenames)
- Modify: `scraper/README.md` (same)
- Modify: `docs/debug-parser-liberty-only-events.md` (~lines 168–169 only — example fixture paths)

**Step 1:** Search-replace path/command examples `2025` → `2026` in those three files. Do **not** change unrelated prose.

**Step 2:** Commit

```bash
git add README.md scraper/README.md docs/debug-parser-liberty-only-events.md
git commit -m "docs: scraper runbooks use 2026 season fixtures"
```

---

### Task 7: Remove 2025 fixtures from the repo

**Files:**
- Delete: all of `scraper/fixtures/team_summary_*_2025*.html` (27 files)

**Step 1:** From project root (PowerShell):

```powershell
Remove-Item "scraper\fixtures\team_summary_*_2025*.html"
```

**Step 2:** Verify no 2025 fixtures remain:

```powershell
Get-ChildItem "scraper\fixtures\team_summary_*_2025*.html"
```

Expected: no output / error that path not found.

**Step 3:** Commit

```bash
git add -A scraper/fixtures
git commit -m "chore(fixtures): remove 2025 team summary HTML snapshots"
```

---

### Task 8: Regenerate full 2026 fixture mirror (method A)

**Requires:** Valid `DATABASE_URL` and `schools` rows with real `athletic_net_team_id` for all nine teams (no `PLACEHOLDER` prefixes). Same conference as today (`--conference-id 1` default).

**Step 1:** Fetch + parse + **write fixtures** for 2026 (rate-limited between schools):

```bash
cd /path/to/conference-leaderboard
python scraper/sync_conference.py --year 2026
```

Expected: console logs one block per school; files appear under `scraper/fixtures/` named `team_summary_<team_id>_2026.html`, `team_summary_<team_id>_2026_women.html`, `team_summary_<team_id>_2026_relays.html`.

**Step 2:** Confirm 27 new files (9 × 3):

```powershell
(Get-ChildItem "scraper\fixtures\team_summary_*_2026*.html").Count
```

Expected: `27`

**Alternative** (if DB not available but network is): for each `team_id` in `TEAM_LABELS` keys, run:

```bash
python scraper/fetch_rendered_html.py <team_id> 2026 all
```

**Step 3:** Commit fixtures

```bash
git add scraper/fixtures
git commit -m "chore(fixtures): add 2026 full conference team summary HTML"
```

---

### Task 9: Verify scraper against new fixtures

**Step 1:** Parser diagnostic (no DB required beyond imports — uses fixtures only):

```bash
python scraper/diagnose_parser.py
```

Expected: non-empty sections for MEN and WOMEN; each school prints athlete counts and event lines without crashing.

**Step 2:** Spot-check inspect scripts (optional):

```bash
python scraper/inspect_all_events.py scraper/fixtures/team_summary_12207_2026_women.html
python scraper/inspect_event_headers.py scraper/fixtures/team_summary_12207_2026.html
```

Expected: runs without traceback; prints event/header info.

**Step 3:** If anything fails, fix parser or fixture fetch before proceeding (do not commit broken fixtures).

---

### Task 10: Next.js lint and production build

**Files:** (read-only verification; may surface unrelated lint — fix only if introduced by this work)

**Step 1:**

```bash
npm install
npm run lint
```

Expected: exit code 0 (or only pre-existing issues documented).

**Step 2:**

```bash
npm run build
```

Expected: `Compiled successfully` / Next.js build completes.

**Step 3:** If only fixture/docs/scraper changes and build already passes, a commit is optional; otherwise commit any required fixes with a clear message.

---

### Task 11: Production / Neon database (operator checklist)

**Not always in repo:** If the deployed app reads marks from Neon, run the same sync against production credentials **after** code defaults are deployed or explicitly pass `--year 2026`:

```bash
# With production DATABASE_URL in env or .env.production.local as your project expects
python scraper/sync_conference.py --year 2026
```

Document in your runbook who runs this and when (e.g. weekly during season).

---

## Summary checklist

| Step | Action |
|------|--------|
| 1–5 | Code defaults + diagnose + helpers |
| 6 | README + debug doc |
| 7 | Delete `*_2025*.html` |
| 8 | `sync_conference.py --year 2026` → 27 files |
| 9 | `diagnose_parser.py` + optional inspect |
| 10 | `npm run lint` + `npm run build` |
| 11 | Neon sync if applicable |

---

**Plan complete and saved to `docs/plans/2026-04-12-2026-season-full-fixtures-cutover.md`. Two execution options:**

**1. Subagent-driven (this session)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. **REQUIRED SUB-SKILL:** `subagent-driven-development` (@`.cursor/skills/subagent-driven-development/SKILL.md`).

**2. Parallel session (separate)** — Open a new session with **REQUIRED SUB-SKILL:** `executing-plans` (@`.cursor/skills/executing-plans/SKILL.md`), optionally after creating a **git worktree** (@`.cursor/skills/using-git-worktrees/SKILL.md`) for the large fixture diff.

**Which approach?**
