# Leaderboard Grade Filter Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure `/api/leaderboard` returns identical results for "no grade filter" and "all grades selected", so manually upserted marks appear in both views.

**Architecture:** Refactor the leaderboard API route to use one SQL path per mode (`pr` and `avg3`) with an optional grade predicate, instead of maintaining separate query branches for grade-filtered vs unfiltered requests. Add focused unit tests around grade parsing and predicate behavior by extracting pure helper functions from the route. Validate parity with live/local API smoke checks.

**Tech Stack:** Next.js App Router (`route.ts`), TypeScript, Neon SQL tagged templates, Vitest (new), ESLint.

---

### Task 1: Add Test Harness + Failing Tests for Grade Filter Behavior

**Files:**
- Create: `vitest.config.ts`
- Modify: `package.json`
- Create: `lib/leaderboard/gradeFilter.ts`
- Test: `lib/leaderboard/gradeFilter.test.ts`

**Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { normalizeGradeFilter, shouldApplyGradeFilter } from "./gradeFilter";

describe("grade filter normalization", () => {
  it("treats missing grades as no filter", () => {
    expect(normalizeGradeFilter(null)).toEqual(null);
    expect(shouldApplyGradeFilter(null)).toBe(false);
  });

  it("normalizes all-grades selection to a concrete filter array", () => {
    const all = normalizeGradeFilter("7,8,9,10,11,12");
    expect(all).toEqual([7, 8, 9, 10, 11, 12]);
    expect(shouldApplyGradeFilter(all)).toBe(true);
  });

  it("drops invalid grade values", () => {
    expect(normalizeGradeFilter("6,7,12,13,abc")).toEqual([7, 12]);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts`  
Expected: FAIL with missing `vitest` script/config and/or missing `gradeFilter` module.

**Step 3: Write minimal implementation**

```ts
export function normalizeGradeFilter(raw: string | null): number[] | null {
  if (!raw) return null;
  const parsed = raw
    .split(",")
    .map((v) => Number(v.trim()))
    .filter((g) => Number.isInteger(g) && g >= 7 && g <= 12);
  return parsed.length > 0 ? parsed : null;
}

export function shouldApplyGradeFilter(grades: number[] | null): grades is number[] {
  return Array.isArray(grades) && grades.length > 0;
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts`  
Expected: PASS.

**Step 5: Commit**

```bash
git add package.json vitest.config.ts lib/leaderboard/gradeFilter.ts lib/leaderboard/gradeFilter.test.ts
git commit -m "test: add grade filter normalization coverage"
```

---

### Task 2: Refactor PR Queries to Single Optional-Filter SQL Path

**Files:**
- Modify: `app/api/leaderboard/route.ts`
- Test: `lib/leaderboard/gradeFilter.test.ts`

**Step 1: Write the failing test**

Add a new test that proves predicate logic can be inserted once:

```ts
import { buildGradePredicateEnabled } from "./gradeFilter";

it("uses one predicate path for filtered and unfiltered requests", () => {
  expect(buildGradePredicateEnabled(null)).toBe(false);
  expect(buildGradePredicateEnabled([11])).toBe(true);
  expect(buildGradePredicateEnabled([7, 8, 9, 10, 11, 12])).toBe(true);
});
```

**Step 2: Run test to verify it fails**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts`  
Expected: FAIL with missing `buildGradePredicateEnabled`.

**Step 3: Write minimal implementation**

1. Extend helper:

```ts
export function buildGradePredicateEnabled(grades: number[] | null): boolean {
  return shouldApplyGradeFilter(grades);
}
```

2. In `route.ts`, replace duplicate `useGradeFilter ? sql\`...\` : sql\`...\`` PR branches with a single query using:

```sql
AND (
  ${useGradeFilter}::int[] IS NULL
  OR a.grade = ANY((${useGradeFilter})::int[])
)
```

Apply this to both PR branches:
- relay PR query (`mode === "pr" && isRelay`)
- individual PR query (`mode === "pr"`)

Keep all existing ordering, season window checks, and sanitization unchanged.

**Step 4: Run tests + lint**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts && npm run lint`  
Expected: PASS.

**Step 5: Commit**

```bash
git add app/api/leaderboard/route.ts lib/leaderboard/gradeFilter.ts lib/leaderboard/gradeFilter.test.ts
git commit -m "fix: unify pr leaderboard grade filter query path"
```

---

### Task 3: Refactor AVG3 Queries to Single Optional-Filter SQL Path

**Files:**
- Modify: `app/api/leaderboard/route.ts`
- Test: `lib/leaderboard/gradeFilter.test.ts`

**Step 1: Write the failing test**

Add parity intent test:

```ts
import { normalizeGradeFilter } from "./gradeFilter";

it("treats omitted grades and explicit all-grades as equivalent intent", () => {
  const omitted = normalizeGradeFilter(null);
  const explicitAll = normalizeGradeFilter("7,8,9,10,11,12");
  expect(omitted).toBeNull();
  expect(explicitAll).toEqual([7, 8, 9, 10, 11, 12]);
});
```

**Step 2: Run test to verify it fails (if needed)**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts`  
Expected: FAIL only if helper behavior is not yet aligned.

**Step 3: Write minimal implementation**

In `route.ts`, replace duplicate AVG3 query branches with the same optional predicate in:
- relay AVG3 (`mode === "avg3" && isRelay`)
- individual AVG3 (`mode === "avg3"`)

Use the same clause pattern:

```sql
AND (
  ${useGradeFilter}::int[] IS NULL
  OR a.grade = ANY((${useGradeFilter})::int[])
)
```

No changes to ranking/window/rounding behavior.

**Step 4: Run tests + lint**

Run: `npm run test -- lib/leaderboard/gradeFilter.test.ts && npm run lint`  
Expected: PASS.

**Step 5: Commit**

```bash
git add app/api/leaderboard/route.ts lib/leaderboard/gradeFilter.test.ts
git commit -m "fix: unify avg3 leaderboard grade filter query path"
```

---

### Task 4: Add API Parity Verification Script + Manual Smoke Checks

**Files:**
- Create: `scripts/verify-leaderboard-grade-parity.mjs`
- Modify: `package.json`
- Test: `scripts/verify-leaderboard-grade-parity.mjs` (script execution)

**Step 1: Write the failing verification script**

```js
const base = process.env.LEADERBOARD_BASE_URL ?? "http://localhost:3000";
const event = "400m";
const gender = "men";
const mode = "pr";
const allGrades = "7,8,9,10,11,12";

const [noFilter, explicitAll] = await Promise.all([
  fetch(`${base}/api/leaderboard?event=${event}&gender=${gender}&mode=${mode}`).then((r) => r.json()),
  fetch(`${base}/api/leaderboard?event=${event}&gender=${gender}&mode=${mode}&grades=${allGrades}`).then((r) => r.json()),
]);

if (JSON.stringify(noFilter.rows) !== JSON.stringify(explicitAll.rows)) {
  console.error("Parity check failed: no-filter rows differ from explicit-all rows");
  process.exit(1);
}
console.log("Parity check passed");
```

**Step 2: Run script to verify it fails before fix (or in current prod)**

Run: `node scripts/verify-leaderboard-grade-parity.mjs`  
Expected: FAIL in current broken state.

**Step 3: Wire script into package commands**

Add:

```json
"verify:leaderboard:parity": "node scripts/verify-leaderboard-grade-parity.mjs"
```

**Step 4: Run script to verify it passes after fix**

Run: `npm run verify:leaderboard:parity`  
Expected: PASS locally; optionally run against prod:

```bash
LEADERBOARD_BASE_URL="https://mcaa-leaderboard.vercel.app" npm run verify:leaderboard:parity
```

**Step 5: Commit**

```bash
git add scripts/verify-leaderboard-grade-parity.mjs package.json
git commit -m "chore: add leaderboard grade parity verification script"
```

---

### Task 5: Deploy + Post-Deploy Validation

**Files:**
- No code changes required unless rollback/hotfix needed.

**Step 1: Run final local verification**

Run:

```bash
npm run test
npm run lint
npm run verify:leaderboard:parity
```

Expected: all PASS.

**Step 2: Deploy**

Run your normal deploy flow (Vercel CLI or Git integration).

**Step 3: Validate live parity**

Check both endpoints and compare:

```bash
curl "https://mcaa-leaderboard.vercel.app/api/leaderboard?event=400m&gender=men&mode=pr"
curl "https://mcaa-leaderboard.vercel.app/api/leaderboard?event=400m&gender=men&mode=pr&grades=7,8,9,10,11,12"
```

Expected: identical `rows` arrays, including Levi `53.13`.

**Step 4: UI verification**

Open:
- `https://mcaa-leaderboard.vercel.app/leaderboard` (all grades)
- same view with grade 11 selected

Expected: Levi appears in both where rank thresholds permit.

**Step 5: Commit (if any deployment metadata changed)**

```bash
git add <deployment-related-files-if-any>
git commit -m "chore: verify leaderboard grade-filter parity in production"
```

---

## Notes for Implementation

- Keep behavior DRY: one SQL text per mode/path, one optional grade predicate.
- Avoid changing ranking semantics beyond this parity fix.
- Do not bundle unrelated cleanup.
- If route refactor grows, extract SQL-building utilities under `lib/leaderboard/` and cover with unit tests first (@test-driven-development).
