# Nightly Refresh Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically re-scrape and refresh 2026 conference marks every night using GitHub Actions, with reliable failure visibility through GitHub notifications.

**Architecture:** Add a scheduled GitHub Actions workflow that runs the existing Python scraper (`scraper/sync_conference.py`) directly against Neon using `DATABASE_URL` secret injection. Keep scraping logic in Python (no new worker service), add workflow-level safeguards (timeout, concurrency, manual trigger), and document operating instructions in project docs.

**Tech Stack:** GitHub Actions (cron + workflow_dispatch), Python 3.11, Playwright Chromium, existing scraper scripts, Neon Postgres.

---

### Task 1: Add Nightly GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/nightly-refresh.yml`
- Reference: `scraper/sync_conference.py`
- Reference: `scraper/requirements.txt`

**Step 1: Write the failing test (workflow validation gate)**

Create a minimal verification command in the workflow that fails if required secret is absent:

```yaml
- name: Validate required env
  run: |
    if [ -z "${DATABASE_URL}" ]; then
      echo "DATABASE_URL is required"
      exit 1
    fi
```

This is the first “red” safety gate for CI behavior.

**Step 2: Run test to verify it fails (in a feature branch without secret)**

Run (manual trigger in GitHub UI):

`Actions -> Nightly refresh -> Run workflow`

Expected: `Validate required env` fails with `DATABASE_URL is required` in environments that do not provide the secret.

**Step 3: Write minimal implementation**

Create `.github/workflows/nightly-refresh.yml` with:

```yaml
name: Nightly Refresh

on:
  schedule:
    - cron: "0 8 * * *" # 2:00 AM America/Chicago during CST; 3:00 AM during CDT
  workflow_dispatch:

concurrency:
  group: nightly-refresh
  cancel-in-progress: false

jobs:
  scrape-refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: scraper/requirements.txt
      - name: Install scraper dependencies
        run: pip install -r scraper/requirements.txt
      - name: Install Playwright Chromium
        run: python -m playwright install --with-deps chromium
      - name: Validate required env
        run: |
          if [ -z "${DATABASE_URL}" ]; then
            echo "DATABASE_URL is required"
            exit 1
          fi
      - name: Run conference sync
        run: python scraper/sync_conference.py --year 2026 --conference-id 1 --no-save-fixtures
```

**Step 4: Run test to verify it passes**

Manual trigger after adding repo secret `DATABASE_URL`.

Expected:
- Workflow starts and completes successfully.
- Logs show schools processed and final `Done.` output from scraper.

**Step 5: Commit**

```bash
git add .github/workflows/nightly-refresh.yml
git commit -m "ci: add nightly GitHub Actions refresh for 2026 scraper sync"
```

---

### Task 2: Make Schedule Behavior Explicit and Safe

**Files:**
- Modify: `.github/workflows/nightly-refresh.yml`
- Modify: `README.md`

**Step 1: Write the failing test**

Define a doc assertion: repository docs must clearly explain UTC schedule behavior and DST caveat for “2 AM Central intent.”

Red state: no explicit scheduling explanation exists for operators.

**Step 2: Run test to verify it fails**

Review `README.md` manually.

Expected fail condition: no “Nightly automation” section with schedule + manual rerun instructions.

**Step 3: Write minimal implementation**

Add a compact section in `README.md`:

```md
## Nightly automation

- Workflow: `.github/workflows/nightly-refresh.yml`
- Schedule: `0 8 * * *` (UTC). This targets ~2:00 AM Central in standard time.
- Manual run: GitHub Actions -> Nightly Refresh -> Run workflow.
- Required secret: `DATABASE_URL`.
```

Optional refinement (if strict local-time behavior is required): replace one cron with two seasonal cron entries and month-guard logic in shell.

**Step 4: Run test to verify it passes**

Manual docs verification checklist:
- Schedule value in docs matches workflow.
- Secret name matches workflow (`DATABASE_URL`).
- Manual rerun path is clear and reproducible.

Expected: all checks pass.

**Step 5: Commit**

```bash
git add README.md .github/workflows/nightly-refresh.yml
git commit -m "docs: document nightly refresh schedule and operator runbook"
```

---

### Task 3: Add Scraper-Specific Operations Notes

**Files:**
- Modify: `scraper/README.md`

**Step 1: Write the failing test**

Define operational acceptance criteria:
- `scraper/README.md` explains nightly CI execution command.
- It explains why `--no-save-fixtures` is used in CI.
- It lists required platform dependency (Playwright Chromium install).

**Step 2: Run test to verify it fails**

Read current `scraper/README.md`.

Expected fail condition: no dedicated “Nightly CI” section with these points together.

**Step 3: Write minimal implementation**

Add section:

```md
## Nightly CI refresh

The GitHub Actions workflow runs:

`python scraper/sync_conference.py --year 2026 --conference-id 1 --no-save-fixtures`

Notes:
- Uses Playwright Chromium in headless mode.
- Uses `DATABASE_URL` from GitHub Actions secrets.
- `--no-save-fixtures` avoids storing HTML artifacts in CI.
```

**Step 4: Run test to verify it passes**

Manual checks:
- Command exactly matches workflow.
- Secret and Chromium dependencies are documented.

Expected: checks pass.

**Step 5: Commit**

```bash
git add scraper/README.md
git commit -m "docs(scraper): add nightly CI refresh instructions"
```

---

### Task 4: Validate End-to-End and Failure Notifications

**Files:**
- No permanent code changes required.
- Optional temporary test branch file to force failure (remove before merge).

**Step 1: Write the failing test**

Design two acceptance tests:
1. **Success path:** Manual workflow run succeeds with valid secret.
2. **Failure path:** Workflow run fails and triggers GitHub failure notification.

**Step 2: Run test to verify it fails (failure path)**

Temporarily force failure in a branch by adding:

```yaml
- name: Force failure test
  run: exit 1
```

Expected:
- Workflow fails predictably.
- GitHub failure notification email arrives.

**Step 3: Write minimal implementation**

Remove the forced-failure step and keep only production workflow steps.

**Step 4: Run test to verify it passes**

Manual trigger final workflow.

Expected:
- Job completes under timeout.
- Leaderboard reflects refreshed data after run.
- No overlapping jobs due to `concurrency` guard.

**Step 5: Commit**

```bash
git add .github/workflows/nightly-refresh.yml
git commit -m "chore: finalize nightly refresh workflow verification"
```

---

### Task 5: Optional Hardening (Only if needed after first week)

**Files:**
- Modify: `.github/workflows/nightly-refresh.yml` (optional)
- Modify: `README.md` (optional)

**Step 1: Write the failing test**

Need stricter confidence that refresh produced non-empty/healthy output (not just exit code success).

**Step 2: Run test to verify it fails**

Observe that current workflow lacks a post-sync sanity check.

**Step 3: Write minimal implementation**

Add one post-sync check (pick one):
- API probe (if deployed): call leaderboard endpoint and assert response has rows.
- DB probe: tiny Python script or SQL call to assert marks count for 2026 > threshold.

**Step 4: Run test to verify it passes**

Manual trigger and confirm sanity-check step passes with expected values.

**Step 5: Commit**

```bash
git add .github/workflows/nightly-refresh.yml README.md
git commit -m "ci: add post-refresh sanity check for nightly scrape"
```

---

## Final Verification Checklist

Run in order:

1. Configure repo secret `DATABASE_URL`.
2. Merge workflow to default branch.
3. Trigger `workflow_dispatch` once and confirm success.
4. Confirm logs include per-school processing and `Done.`.
5. Confirm leaderboard shows expected refreshed marks.
6. Validate GitHub notification settings by intentionally failing one branch run.

If all six checks pass, nightly automation is production-ready.
