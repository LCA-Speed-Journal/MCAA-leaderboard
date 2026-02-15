# Leaderboard UI Polish — Design

**Date:** 2026-02-15  
**Status:** Validated  
**Scope:** Functional and visual polish for the MCAA Conference Leaderboard.

---

## 1. Scope, data, and API

### In scope

- **Mark provenance tooltip** — On hover over the mark cell: PR = single date + meet name; Avg of last 3 = date range only (e.g. "Dec 10, 2025 – Jan 15, 2026"). No new column; tooltip only.
- **Grade filter** — Multi-select for grades **7–12**. No selection = all grades; when one or more grades selected, only those grades; athletes with NULL grade are excluded.
- **Grade next to name** — In the Athlete column: "Name — 10" with "— 10" in grey, lighter weight (e.g. `text-gray-500 font-normal`). If grade is null, show name only.
- **Visual hierarchy** — Athlete name and mark bold; school name italic. Table order remains Rank → Athlete (with grade) → School → Mark.
- **Less flat look** — Soft page background, subtle table container (card) so the table isn’t the only surface.
- **School color-coding** — Add `primary_color` and `secondary_color` (or `accent_color`) to `schools` via migration + seed. UI: left-edge row accent (primary) + school name in primary color.

### Data and API

- **Leaderboard API** returns per row: existing fields plus `grade` (number | null), and provenance:
  - **PR:** `mark_date`, `meet_name` (for the single PR mark).
  - **Avg3:** `mark_date_min`, `mark_date_max` (date range of the three marks).
- **Grade filter:** New query param `grades=9,10` (comma-separated). Omit = all grades; when present, `WHERE grade = ANY($1)` and exclude NULL.
- **Schools/colors:** Migration adds `primary_color TEXT`, `secondary_color TEXT` (hex). Seed with values per school. Leaderboard response includes `school_id`; add GET **/api/schools** (or include school list with colors in config) so the client can map `school_id` → colors for left accent and colored school name.

---

## 2. UI components and behavior

### Filter strip

- Existing: Event (grouped select), Gender (men/women), View by (PR / Avg of last 3).
- **Grade:** Multi-select for grades **7, 8, 9, 10, 11, 12**. Options as checkboxes in a dropdown or pill toggles; multiple can be active. When none active = "all grades." Send `grades` only when at least one grade is selected.
- Label: e.g. "Grade (optional; leave unselected for all)."

### Table structure

- Columns: Rank | Athlete | School | Mark.
- **Athlete:** "Name — 10" — name bold, " — 10" grey, lighter weight. If grade null: "Name" only.
- **School:** Italic, colored with school `primary_color`; fallback to neutral if missing or too light for contrast.
- **Mark:** Bold; same formatting (time/distance/feet-inches). This cell is the hover target for the provenance tooltip.
- **Row:** Thin left border (3–4px) in school `primary_color`. Row key: rank+name+school+value+index.

### Mark provenance tooltip

- Trigger: hover or focus on the **Mark** cell.
- **PR:** "PR set on &lt;date&gt;" then meet name if present; if `meet_name` null, date only.
- **Avg3:** "Avg of last 3: &lt;date_min&gt; – &lt;date_max&gt;" (no meet names).
- Prefer a small custom tooltip component (positioned div) for formatting and accessibility; ensure keyboard focus triggers it and screen readers get the text (e.g. `aria-describedby`).

### Schools and colors

- Fetch school list with colors once (GET /api/schools or config). Map `school_id` → `{ primary_color, secondary_color }`. Apply primary to left border and school name; if no color, use neutral (e.g. gray).

---

## 3. Visual theme and polish

### Background and container

- **Page background:** Soft (e.g. `gray-100` or light warm gray).
- **Table container:** Card-style — white/near-white, `shadow-sm`, rounded corners. Benchmarks block in same card above table or matching card.

### Typography

- **Table header:** Muted (e.g. `text-gray-600`), medium weight; optional subtle bottom border.
- **Table body:** Athlete name and mark **bold**; school **italic** and in primary color. Body text readable neutral (e.g. `gray-800`). Rank normal weight, can stay muted.

### Empty and error states

- No marks: existing copy; style to match card.
- Error: red alert inside/above card.
- Grade filter applied but no athletes in selected grades: "No athletes in selected grades" or reuse empty state.

### Mobile

- Filters stack/wrap; grade multi-select remains usable. Table horizontal scroll; left accent and colored school name still visible.

---

## 4. Implementation checklist (reference)

- [ ] Migration: add `primary_color`, `secondary_color` to `schools`; seed hex values.
- [ ] API: GET /api/schools returning id, name, primary_color, secondary_color.
- [ ] API: leaderboard returns grade, school_id, mark_date, meet_name (PR) or mark_date_min, mark_date_max (Avg3); add `grades` query param and filter (exclude NULL when grades specified).
- [ ] UI: grade multi-select 7–12; wire to `grades` param (omit when empty).
- [ ] UI: athlete column "Name — grade" with grey grade; school italic + primary color; mark bold; row left accent.
- [ ] UI: mark cell tooltip (custom component) with PR vs Avg3 content.
- [ ] UI: page background + card container; benchmarks in card; typography and empty/error states as above.
