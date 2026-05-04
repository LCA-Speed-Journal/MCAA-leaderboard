#!/usr/bin/env python3
"""
Fetch and load marks for all schools in the conference from the database.
Uses Playwright (like sync_school.py) so Angular team-summary pages render correctly.
Skips schools whose athletic_net_team_id starts with "PLACEHOLDER".

Usage (from project root; DATABASE_URL in .env.local):
  python scraper/sync_conference.py [--year YEAR] [--conference-id ID] [--gender GENDER] [--no-save-fixtures]

Example:
  python scraper/sync_conference.py
  python scraper/sync_conference.py --year 2026 --gender men
  python scraper/sync_conference.py --gender women --no-save-fixtures

Requires: pip install playwright && python -m playwright install chromium
"""
import argparse
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local", override=True)
except ImportError:
    pass

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and load all marks for every school in the conference (Playwright)."
    )
    parser.add_argument("--year", default="2026", help="season year (default: 2026)")
    parser.add_argument("--conference-id", type=int, default=1, help="conference id (default: 1)")
    parser.add_argument(
        "--gender",
        choices=("all", "men", "women"),
        default="all",
        help="sync only men, only women, or all (default: all)",
    )
    parser.add_argument(
        "--no-save-fixtures",
        action="store_true",
        help="do not write HTML files to scraper/fixtures",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        psycopg2 = None

    from run import fetch_schools, parse_team_summary, upsert_athletes_marks, get_db, RATE_LIMIT_SEC
    from fetch_rendered_html import fetch_one, FIXTURES_DIR

    conn = get_db()
    try:
        schools = fetch_schools(conn, conference_id=args.conference_id)
    finally:
        conn.close()

    real_schools = [
        (school_id, team_id, name)
        for school_id, team_id, name in schools
        if not (str(team_id).upper().startswith("PLACEHOLDER"))
    ]

    if not real_schools:
        print("No schools with real athletic.net team IDs found. Update seed or DB.")
        sys.exit(1)

    gender = args.gender
    if gender != "all":
        print(f"Found {len(real_schools)} school(s) to sync ({gender} only). Rate limit: {RATE_LIMIT_SEC}s between schools.")
    else:
        print(f"Found {len(real_schools)} school(s) to sync. Rate limit: {RATE_LIMIT_SEC}s between schools.")
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    url_tpl = "https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ua_headers = {"User-Agent": "ConferenceLeaderboard/1.0 (school use)"}

        for i, (school_id, team_id, name) in enumerate(real_schools):
            page = browser.new_page()
            page.set_extra_http_headers(ua_headers)
            saw_cloudflare = False
            try:
                url = url_tpl.format(team_id=team_id, year=args.year)
                print(f"[{i + 1}/{len(real_schools)}] {name} (team {team_id}) ...")

                views_to_fetch = (
                    ("men", "relays") if gender == "men"
                    else ("women", "relays") if gender == "women"
                    else ("men", "women", "relays")
                )
                html_by_view = {}
                for view in views_to_fetch:
                    try:
                        html, out_path = fetch_one(page, url, view, str(team_id), args.year)
                        html_by_view[view] = html
                        if not args.no_save_fixtures:
                            with open(out_path, "w", encoding="utf-8") as f:
                                f.write(html)
                    except Exception as e:
                        print(f"  Warning: {view} failed: {e}")
                        html_by_view[view] = ""
                        msg = str(e)
                        if isinstance(e, RuntimeError) and "Cloudflare" in msg:
                            saw_cloudflare = True
                        elif "Attention Required" in msg or "Just a moment" in msg:
                            saw_cloudflare = True
            finally:
                page.close()

            # Fresh DB connection per school so Neon does not close an idle socket during long scrapes.
            steps = (
                [("men", html_by_view.get("men", ""), "men"), ("relays (men)", html_by_view.get("relays", ""), "men")]
                if gender == "men"
                else [("women", html_by_view.get("women", ""), "women"), ("relays (women)", html_by_view.get("relays", ""), "women")]
                if gender == "women"
                else [
                    ("men", html_by_view.get("men", ""), "men"),
                    ("women", html_by_view.get("women", ""), "women"),
                    ("relays (men)", html_by_view.get("relays", ""), "men"),
                    ("relays (women)", html_by_view.get("relays", ""), "women"),
                ]
            )

            def _run_upserts(connection):
                for label, html, g in steps:
                    if not html:
                        continue
                    athletes = parse_team_summary(html, school_id, g)
                    if athletes:
                        upsert_athletes_marks(connection, school_id, g, athletes)
                        print(f"  {label}: {len(athletes)} athletes")

            db_conn = get_db()
            try:
                try:
                    _run_upserts(db_conn)
                except Exception as e:
                    if psycopg2 is not None and isinstance(e, psycopg2.OperationalError):
                        try:
                            db_conn.close()
                        except Exception:
                            pass
                        db_conn = get_db()
                        _run_upserts(db_conn)
                    else:
                        raise
            finally:
                db_conn.close()

            if i < len(real_schools) - 1:
                pause = RATE_LIMIT_SEC
                if saw_cloudflare:
                    extra = 45
                    print(f"  Pausing {extra}s extra after Cloudflare before the next school.")
                    pause += extra
                time.sleep(pause)

        browser.close()

    print("Done.")


if __name__ == "__main__":
    main()
