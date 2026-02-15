# Systematic Debugging Report: Leaderboard Only Showing Liberty for Certain Events

**Date:** 2026-02-15  
**Scope:** Scraper/parser and data flow for events where only Liberty marks appear (100m, 800m, 1600m, 110h, 100h, 4x100, HJ, Shot Put, Discus).

---

## Phase 1: Root Cause Investigation

### 1.1 Evidence Gathered

**Parser diagnostic (fixture files):**

- Ran `diagnose_parser.py` on all school fixtures (men + women).
- **Result:** From the **saved fixture HTML**, the parser produces marks for **all schools** for 1600m, 800m, 100m, 110h (men), 100h (women), shot put, discus, high jump. Liberty is not special in the fixtures — every school’s HTML that contains those events parses successfully.

**Event header inspection:**

- Liberty men (73442): First athlete has 10 event headers (100m, 200m, 400m, lj, tj, …). All map to slugs.
- CHOF men (12207): First athlete has 6 headers (800m, 1600m, hj). No 110h in **this** athlete’s block; CHOF men fixture has **no** 110h sections at all → **data**: no male 110h runners in that fixture, not a label bug.
- CHOF women (12207): Labels include "Shot Put - 4kg" → sp, "Discus - 1kg" → discus. No "100m Hurdles" (or variant) in the fixture → **data**: no female 100h in that CHOF women fixture. One unmapped label: **"50 Meter"** (indoor/short sprint).

**Relays:**

- 4x100 (and other relays) are on the **Relays** tab. In the diagnostic we only parsed the main men/women HTML files; relays are in `*_relays.html`. Sync does fetch relays and parses with `_parse_athletic_net_relays(soup, gender)`. So 4x100 should appear for all schools that have relay data in the relays fixture.

**API / DB:**

- Leaderboard API (`app/api/leaderboard/route.ts`) does **not** filter by school. It queries marks by `event` slug and `gender` only. So if the leaderboard shows only Liberty for an event, the **database** only has marks for that event from Liberty’s athletes.

**Sync flow:**

- `sync_conference.py` loops over all schools, builds URL per `team_id`, fetches men/women/relays per school, parses, and calls `upsert_athletes_marks(conn, school_id, g, athletes)`. So each school’s data is stored under its own `school_id`. No overwrite of one school by another in the code.

### 1.2 Findings

| Finding | Implication |
|--------|-------------|
| Fixture parser output is multi-school | The bug is **not** “parser only works for Liberty.” On saved HTML, all schools that have the event get marks. |
| API does not filter by school | If only Liberty shows, the DB has only Liberty’s marks for that event. |
| CHOF (and possibly others) have no 110h/100h in **fixture** | For some schools the **saved** fixture simply has no athletes in those events. That can be fixture-specific (e.g. one snapshot). |
| Discus min filter | `DISTANCE_MIN_METERS["discus"] = 15.0` — marks under 15m are dropped. Smaller conferences / younger athletes often throw under 15m → **valid marks can be rejected**. |
| 4x100 only on Relays tab | If relays HTML is missing or fails to load for a school, that school would have no 4x100 in the DB. |

### 1.3 Likely Root Causes (in order)

1. **Data load / sync history**  
   Only Liberty’s data may have been loaded for those events (e.g. only Liberty fixtures ever loaded, or sync has only been run successfully for Liberty in the environment you’re viewing).

2. **Live HTML differs from fixtures**  
   When sync runs with Playwright, non-Liberty schools might get a different DOM (e.g. different Angular build, failed tab switch, or timeout) so that for those schools the parser gets no or fewer athletes for the affected events.

3. **Relays tab or Women tab failing for some schools**  
   If `fetch_one(page, url, view, ...)` fails for "relays" or "women" for non-Liberty schools (timeout or selector), those views would be empty and we’d store no relays or no women’s data for that school.

4. **Plausibility filters dropping valid marks**  
   - Discus: `DISTANCE_MIN_METERS["discus"] = 15.0` can drop valid throws &lt; 15m.  
   - Other distance/time bounds could in theory drop edge-case valid marks.

---

## Phase 2: Pattern Analysis

- **Working reference:** Liberty’s fixtures parse and produce marks for all focus events.
- **Same code path:** All schools use the same `parse_team_summary` → `_parse_athletic_net_angular` (or relays fallback) and same `upsert_athletes_marks`.
- **Difference:** Either (a) which HTML is actually fetched and stored (sync/load), or (b) which data exists in the HTML (e.g. no 110h at CHOF in the fixture), or (c) filters (e.g. discus min) removing marks for some schools.

---

## Phase 3: Recommended Next Steps (no code changes yet)

1. **Verify DB state**  
   Run a query like:
   ```sql
   SELECT e.slug, s.name AS school_name, COUNT(*) AS mark_count
   FROM marks m
   JOIN athletes a ON a.id = m.athlete_id
   JOIN schools s ON s.id = a.school_id
   JOIN events e ON e.id = m.event_id
   WHERE e.slug IN ('1600m', '100h', '110h', 'sp', 'discus', '4x100', '100m', '800m', 'hj')
   GROUP BY e.slug, s.name
   ORDER BY e.slug, s.name;
   ```
   If only Liberty has rows for certain slugs, the issue is upstream (sync/load or live HTML), not the API.

2. **Confirm sync runs for all schools**  
   On the next sync, ensure logs show each school’s name/team_id and that men, women, and relays all report “N athletes” where N &gt; 0 when that school has data. Any “Warning: … failed” for a view means no data for that school/gender/view.

3. **Optional: relax discus minimum**  
   If you want to include smaller throws (e.g. middle school or lighter implement), consider lowering `DISTANCE_MIN_METERS["discus"]` (e.g. to 10.0) and document the choice.

4. **Optional: map "50 Meter"**  
   If you care about 50m (e.g. indoor), add a mapping in `EVENT_TO_SLUG`; otherwise leave as unmapped.

---

## Update: DB has marks for all schools

If the database query shows marks for **all schools** in the affected events, then the problem is **not** in the scraper or DB — it is in the **display layer** (API or frontend).

### Narrowing it down

1. **Check the API response**  
   Open DevTools → Network, select the leaderboard request (e.g. `GET .../api/leaderboard?event=1600m&gender=men&mode=pr`), and look at the response body.  
   - If `rows` contains entries for **multiple schools** but the table only shows Liberty → the bug is in the **frontend** (e.g. React key collision, or a filter in the UI).  
   - If `rows` contains **only Liberty** → the **database that the app is using** only has Liberty’s marks for that event (see below).

2. **Confirm which app you’re viewing**  
   If the leaderboard you use is from **LCA-Speed_Vercel** (or another repo), it may have its own API and DB. In that case, the display bug or data filter could be in that app, not in this conference-leaderboard codebase.

3. **Frontend**  
   This app’s leaderboard page simply does `setRows(lb.rows || [])` and maps over `rows`; there is no client-side filter by school. The row key includes `i`, so duplicate keys should not collapse rows. If the API returns all schools and only one appears, the next place to check is any wrapper or layout that might be filtering or limiting the list.

### Verify per-school distribution in the DB

Run this in Neon (or `psql` with your `DATABASE_URL`) to see how many **marks** and **distinct athlete bests** per school for an event. That shows whether the 759 rows are all Liberty or spread across schools.

```sql
-- Marks per school for 1600m (event slug); use e.slug = '100m' for 100m
SELECT s.name AS school_name,
       COUNT(*) AS mark_count,
       COUNT(DISTINCT a.id) AS athlete_count
FROM marks m
JOIN athletes a ON a.id = m.athlete_id
JOIN schools s ON s.id = a.school_id
JOIN events e ON e.id = m.event_id
WHERE e.slug = '1600m'
  AND a.gender = 'M'
GROUP BY s.id, s.name
ORDER BY s.name;
```

If this returns **one row** (Liberty only), then the DB really only has Liberty’s data for that event. If it returns **multiple schools**, then the API query should return multiple schools too — and you can confirm what the API sees via the server log (see below).

### When the API returns only Liberty (confirmed)

If the Network tab shows `rows` with only "Liberty Classical Academy", then the API is correctly returning what’s in **the database the app is connected to** — and that database only has Liberty’s marks for that event. The SQL does not filter by school.

So either:

- **Different databases:** The verification query you ran earlier may have used a *different* database (e.g. Neon SQL editor on another branch, or a different `DATABASE_URL`). The Next.js app uses `DATABASE_URL` from the environment that serves the request (e.g. `.env.local` when running `npm run dev`, or the Vercel project env when deployed). Run the same verification query using the **exact same** `DATABASE_URL` the app uses (connect with `psql "$DATABASE_URL"` or Neon’s SQL editor for that connection string). If that DB only has Liberty for 100m men, the fix is to **backfill that DB** with all schools.

- **Backfill the app’s database:** Run the full sync against the **same** `DATABASE_URL` the app uses:
  ```bash
  # From project root, with the same .env.local the app uses
  python scraper/sync_conference.py
  ```
  That will fetch and upsert all schools’ data into the DB. After it finishes, reload the leaderboard; you should see all schools for 100m and other events.

- **Server log diagnostic:** The leaderboard API now logs each request to the server console, e.g.:
  `[leaderboard] event=1600m gender=men mode=pr: rows=85 schools=9 [Liberty Classical Academy, ...]`
  Run `npm run dev`, open the leaderboard for 1600m men, and check the **terminal** where Next.js is running. If it shows `schools=1` and only Liberty, the query is only returning Liberty (same DB, so something in the query or data). If it shows `schools=9`, the API is returning all schools and the problem would be elsewhere (e.g. response not reaching the client).

---

## Phase 4: Implementation (only after confirming root cause)

- **Do not** change parser logic or add “Liberty-specific” branches. The parser behaves the same for all schools on the same HTML.
- **If** DB verification shows only Liberty has marks: fix data loading (ensure full sync for all schools and that all three views are fetched and parsed per school).
- **If** discus counts are low for multiple schools: consider lowering `DISTANCE_MIN_METERS["discus"]` and re-running sync.
- **If** relays are missing for non-Liberty: ensure relays tab loads for every school (logging, timeouts, selectors in `fetch_rendered_html.py` / `fetch_one`).

---

## Diagnostic Scripts Added

- **`scraper/diagnose_parser.py`** — Parses all men’s and women’s fixtures and prints per-school, per-event mark counts for the focus events. Run from project root: `python scraper/diagnose_parser.py`.
- **`scraper/inspect_event_headers.py`** — Prints event headers and slug resolution for the first athlete block in a given HTML file. Example: `python scraper/inspect_event_headers.py scraper/fixtures/team_summary_12207_2025.html`.
- **`scraper/inspect_all_events.py`** — Collects all unique event labels in a fixture and reports mapped vs unmapped. Example: `python scraper/inspect_all_events.py scraper/fixtures/team_summary_12207_2025_women.html`.

Use these to compare schools and to validate after any parser or sync changes.
