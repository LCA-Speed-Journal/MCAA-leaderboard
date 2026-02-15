# Leaderboard UI Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement functional and visual polish for the MCAA Conference Leaderboard per design doc `docs/plans/2026-02-15-leaderboard-ui-polish-design.md`: mark provenance tooltips, grade filter (7–12), grade next to athlete name, school color-coding, and card-based layout with improved typography.

**Architecture:** Backend: one migration adds `primary_color` and `secondary_color` to `schools` and seeds hex values; new GET `/api/schools` returns school list with colors; GET `/api/leaderboard` gains optional `grades` query param and response fields `grade`, `school_id`, and provenance (`mark_date`/`meet_name` for PR, `mark_date_min`/`mark_date_max` for Avg3). Frontend: leaderboard page adds grade multi-select, fetches schools for colors, renders table with athlete+grade, colored school name, row left accent, mark cell tooltip, and card/background styling.

**Tech Stack:** Next.js 14, React 18, Tailwind CSS, Neon PostgreSQL, `@neondatabase/serverless`.

---

## Task 1: Migration — add school colors

**Files:**
- Create: `migrations/005_school_colors.sql`
- Test: run migration then `SELECT primary_color, secondary_color FROM schools LIMIT 1;`

**Step 1: Create migration file**

Add columns and seed hex values (one color per school; adjust hex to taste later).

```sql
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
```

**Step 2: Run migration**

Run: `psql $DATABASE_URL -f migrations/005_school_colors.sql`  
Expected: ALTER TABLE and UPDATE statements execute without error.

**Step 3: Verify**

Run: `psql $DATABASE_URL -c "SELECT id, name, primary_color FROM schools LIMIT 2;"`  
Expected: Two rows with non-null `primary_color`.

**Step 4: Commit**

```bash
git add migrations/005_school_colors.sql
git commit -m "feat(db): add primary_color, secondary_color to schools and seed"
```

---

## Task 2: GET /api/schools

**Files:**
- Create: `app/api/schools/route.ts`
- Test: manual `curl` or browser GET `/api/schools`

**Step 1: Create route**

```typescript
// app/api/schools/route.ts
import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const sql = getSql();
  try {
    const rows = await sql`
      SELECT id, name, primary_color, secondary_color
      FROM schools
      ORDER BY name
    `;
    return NextResponse.json({ schools: rows });
  } catch (err) {
    console.error("Schools API error:", err);
    return NextResponse.json(
      { error: "Failed to load schools" },
      { status: 500 }
    );
  }
}
```

**Step 2: Run dev server and verify**

Run: `npm run dev`  
Then: `curl -s http://localhost:3000/api/schools | head -c 500`  
Expected: JSON with `schools` array; each item has `id`, `name`, `primary_color`, `secondary_color`.

**Step 3: Commit**

```bash
git add app/api/schools/route.ts
git commit -m "feat(api): add GET /api/schools with colors"
```

---

## Task 3a: Leaderboard API — parse grades param and filter

**Files:**
- Modify: `app/api/leaderboard/route.ts` (full file; add grades parsing and use in all four query branches)

**Step 1: Parse grades param**

After parsing `event`, `gender`, `mode`, add:

- Read `grades` from searchParams (e.g. `searchParams.get("grades")`).
- If present: split by comma, map to integers, filter to 7–12 only. If resulting array empty, treat as “no filter”.
- When grades array has length > 0: in every leaderboard query add `AND a.grade = ANY(${gradesArray})` (and ensure `a.grade` is not used in GROUP BY in a way that breaks; for relay, filter is on athletes that make up the school’s marks). For relay queries, the filter is “only schools that have at least one athlete in the selected grades” — for MVP, filter relay by same grade logic on the underlying athletes (e.g. in school_best / school_performances CTEs, join athletes and add `AND (cardinality(gradesArray) = 0 OR a.grade = ANY(gradesArray))`).

Use a single variable, e.g. `const gradeFilter = gradesParam ? validGrades : null` where `validGrades` is number[] (7–12). In SQL, when `gradeFilter` is non-null use `AND a.grade = ANY(${gradeFilter})` in the WHERE of each CTE that joins `athletes a`.

**Step 2: Implement in code**

- Parse: `const gradesParam = searchParams.get("grades"); const gradeFilter = gradesParam ? gradesParam.split(",").map(Number).filter((g) => g >= 7 && g <= 12) : null;` (use empty array as “no filter” if parsed result is empty).
- In each of the four branches (PR relay, PR individual, Avg3 relay, Avg3 individual), add to the WHERE clause of the CTE that references `athletes`:  
  `...(gradeFilter === null || gradeFilter.length === 0 ? sql`` : sql` AND a.grade = ANY(${gradeFilter})`)...`  
  Use tagged template from `getSql()` for the array param (Neon accepts array for `= ANY($1)`).

**Step 3: Verify**

Call `GET /api/leaderboard?event=100m&gender=men&mode=pr` — same as before.  
Call `GET /api/leaderboard?event=100m&gender=men&mode=pr&grades=9,10` — fewer rows if DB has grade data; no 500.

**Step 4: Commit**

```bash
git add app/api/leaderboard/route.ts
git commit -m "feat(api): leaderboard grades filter (grades=7,8,...,12)"
```

---

## Task 3b: Leaderboard API — return grade, school_id, and provenance

**Files:**
- Modify: `app/api/leaderboard/route.ts`

**Step 1: PR individual — return grade, school_id, mark_date, meet_name**

Change the PR (non-relay) query so the “best” mark per athlete is one row (use DISTINCT ON (a.id) ordered by value asc/desc by event direction), then select: rank, athlete_name, school_name, school_id, grade, value, mark_date, meet_name. Example shape:

- CTE: get best mark per athlete with `DISTINCT ON (a.id)` and ORDER BY value (asc for lower, desc for higher), include m.mark_date, m.meet_name, a.grade, s.id AS school_id, s.name AS school_name, a.name AS athlete_name.
- Outer: ROW_NUMBER() OVER (ORDER BY value …) AS rank, then SELECT rank, athlete_name, school_name, school_id, grade, value, mark_date, meet_name.

Apply same grade filter (AND a.grade = ANY when gradeFilter length > 0). Sanitize `value` with existing `sanitizeDistanceValue` before returning.

**Step 2: PR relay — return school_id, mark_date, meet_name**

In the relay PR query, the “value” is MIN(m.value) per school. Add columns: for that same MIN(m.value), pick one row’s mark_date and meet_name (e.g. use a subquery or DISTINCT ON per school). Return school_id (already have s.id), mark_date, meet_name. No grade for relay.

**Step 3: Avg3 individual — return grade, school_id, mark_date_min, mark_date_max**

In the Avg3 (non-relay) CTE, compute MIN(m.mark_date) and MAX(m.mark_date) over the same three marks used for AVG(value). Add to SELECT: a.grade, s.id AS school_id, and in the CTE that has the three marks use MIN(m.mark_date) AS mark_date_min, MAX(m.mark_date) AS mark_date_max. Expose in final SELECT. Keep grade filter.

**Step 4: Avg3 relay — return school_id, mark_date_min, mark_date_max**

In relay Avg3 CTE, for each school’s last three performances compute MIN(mark_date), MAX(mark_date). Add to final SELECT: school_id (s.id), mark_date_min, mark_date_max.

**Step 5: Type and response shape**

Ensure every leaderboard row type includes: rank, athlete_name, school_name, school_id, value, grade (number | null), and either (mark_date, meet_name) for PR or (mark_date_min, mark_date_max) for Avg3. Relay rows may have grade null.

**Step 6: Verify**

GET leaderboard with mode=pr and mode=avg3; check JSON has school_id, grade, and provenance fields.

**Step 7: Commit**

```bash
git add app/api/leaderboard/route.ts
git commit -m "feat(api): leaderboard returns grade, school_id, and mark provenance"
```

---

## Task 4: UI — Grade multi-select filter

**Files:**
- Modify: `app/leaderboard/page.tsx`

**Step 1: Add state and fetch URL**

- Add state: `const [grades, setGrades] = useState<number[]>([]);` (empty = “all grades”).
- Build leaderboard URL: base + (grades.length ? `&grades=${grades.join(",")}` : "").

**Step 2: Add Grade filter UI**

- Label: “Grade (optional; leave unselected for all).”
- Options: 7, 8, 9, 10, 11, 12. Use checkboxes in a dropdown or pill toggles; multiple can be active.
- Toggle: clicking a grade adds/removes it from `grades`; when none selected, do not send `grades` param.

**Step 3: Wire to fetch**

In the `useEffect` that fetches leaderboard, add `grades` to the dependency array and include `grades` in the query string when `grades.length > 0`.

**Step 4: Verify**

Select one or more grades; table updates. Deselect all; table shows all grades again.

**Step 5: Commit**

```bash
git add app/leaderboard/page.tsx
git commit -m "feat(ui): grade multi-select filter (7–12)"
```

---

## Task 5: UI — Schools colors, athlete grade, school italic, row accent

**Files:**
- Modify: `app/leaderboard/page.tsx`

**Step 1: Fetch schools and types**

- On mount (or once), fetch GET /api/schools. Store in state: `schools: { id: number; name: string; primary_color: string | null; secondary_color: string | null }[]`.
- Extend LeaderboardRow type: add `grade: number | null`, `school_id: number`, and provenance: `mark_date?: string; meet_name?: string | null;` and `mark_date_min?: string; mark_date_max?: string;`.

**Step 2: Athlete column**

- Render: `{row.athlete_name}{row.grade != null ? <> — <span className="text-gray-500 font-normal">{row.grade}</span></> : null}`. Keep athlete name bold (existing or add font-semibold).

**Step 3: School column**

- Map `row.school_id` to school from `schools`; use `primary_color` for text color. Apply `italic`. If no color or too light, use neutral (e.g. `text-gray-700`). Example: `style={{ color: primaryColor ?? undefined }}` and class `italic`.

**Step 4: Row left accent**

- Each `<tr>`: add left border (3–4px) using school primary_color: `style={{ borderLeftWidth: 4, borderLeftColor: primaryColor || "#e5e7eb" }}`.

**Step 5: Mark cell**

- Keep mark value bold; this cell will get the tooltip in Task 6. No change to value formatting yet.

**Step 6: Row key**

- Keep key as `rank-name-school-value-index` per design.

**Step 7: Verify**

Table shows “Name — 10”, italic colored school names, and colored left border per row.

**Step 8: Commit**

```bash
git add app/leaderboard/page.tsx
git commit -m "feat(ui): athlete grade, school color and italic, row left accent"
```

---

## Task 6: UI — Mark provenance tooltip

**Files:**
- Create: `app/leaderboard/MarkTooltip.tsx` (or inline in page)
- Modify: `app/leaderboard/page.tsx` (use tooltip on mark cell)

**Step 1: Tooltip component**

- Props: `mode: "pr" | "avg3"`, provenance: PR = `{ mark_date?: string; meet_name?: string | null }`, Avg3 = `{ mark_date_min?: string; mark_date_max?: string }`. Children: the mark value (bold).
- On hover/focus of wrapper: show a positioned div (e.g. absolute, near the cell) with:
  - PR: “PR set on &lt;formatted date&gt;” then meet name if present; else date only.
  - Avg3: “Avg of last 3: &lt;date_min&gt; – &lt;date_max&gt;”.
- Format dates (e.g. “Dec 10, 2025”) with a small helper or Intl.DateTimeFormat.
- Use `aria-describedby` and a visible description element for screen readers; ensure keyboard focus shows tooltip (e.g. focus within the mark cell).

**Step 2: Wrap mark cell**

- In the table, the Mark cell content: wrap `formatValue(row.value)` in `<MarkTooltip mode={mode} ... provenance={...}>...</MarkTooltip>` and pass the correct provenance from the row.

**Step 3: Handle missing provenance**

- If mark_date/meet_name or date_min/date_max are missing, show “—” or “No date” in tooltip.

**Step 4: Verify**

Hover/focus on mark cell shows correct PR or Avg3 text. No layout shift; tooltip doesn’t overflow viewport (optional: nudge position).

**Step 5: Commit**

```bash
git add app/leaderboard/MarkTooltip.tsx app/leaderboard/page.tsx
git commit -m "feat(ui): mark cell provenance tooltip (PR / Avg3)"
```

---

## Task 7: UI — Page background, card container, typography, empty/error states

**Files:**
- Modify: `app/leaderboard/page.tsx`
- Optionally: `app/globals.css` if needed for page background

**Step 1: Page background**

- Set main container or body section to soft background, e.g. `className="min-h-screen bg-gray-100 p-4 md:p-8"` (or light warm gray).

**Step 2: Card container**

- Wrap table and benchmarks in a card: white/near-white background, `shadow-sm`, rounded corners (e.g. `rounded-lg`). Put benchmarks block in same card above table or in a matching card.

**Step 3: Table header**

- Muted: `text-gray-600`, medium weight; optional subtle bottom border on `<thead>`.

**Step 4: Table body**

- Athlete name and mark bold; school italic (already done); body text `text-gray-800`. Rank normal weight, can stay muted.

**Step 5: Empty and error states**

- No marks: keep existing copy; style to match card (inside card).
- Error: red alert inside/above card (e.g. `bg-red-50 text-red-700`).
- Grade filter applied but no results: show “No athletes in selected grades” or reuse empty state message when `rows.length === 0 && grades.length > 0`.

**Step 6: Mobile**

- Filters: stack/wrap (existing flex-wrap). Grade multi-select remains usable (e.g. checkboxes or pills wrap). Table: keep `overflow-x-auto`; left accent and colored school name still visible.

**Step 7: Verify**

Visual pass: background, card, typography, empty/error and “no athletes in selected grades” all match design.

**Step 8: Commit**

```bash
git add app/leaderboard/page.tsx app/globals.css
git commit -m "feat(ui): card layout, background, typography, empty/error states"
```

---

## Reference

- Design: `docs/plans/2026-02-15-leaderboard-ui-polish-design.md`
- API/DB patterns: `agent_docs/code_patterns.md`
- Testing: `agent_docs/testing.md` (manual verification and curl for API; no test runner in repo yet)

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-02-15-leaderboard-ui-polish-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Parallel Session (separate)** — Open a new session with executing-plans, batch execution with checkpoints.

Which approach?

- If **Subagent-Driven** chosen: **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development; stay in this session; fresh subagent per task + code review.
- If **Parallel Session** chosen: Guide to open new session in worktree; **REQUIRED SUB-SKILL:** New session uses superpowers:executing-plans.
