#!/usr/bin/env python3
"""
Fetch men, women, and relays for one school with Playwright, then parse and upsert
all marks into the database in one run. Single command per school.

Usage (from project root; DATABASE_URL in .env.local):
  python scraper/sync_school.py <team_id> <school_id> [--year YEAR]

Example (Liberty Classical Academy, athletic.net team 73442, school_id 1):
  python scraper/sync_school.py 73442 1
  python scraper/sync_school.py 73442 1 --year 2025

Requires: pip install playwright && python -m playwright install chromium
"""
import argparse
import os
import sys
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
        description="Fetch and load all marks for one school (men, women, relays) in one run."
    )
    parser.add_argument("team_id", help="athletic.net team ID (e.g. 73442)")
    parser.add_argument("school_id", type=int, help="school id in your schools table")
    parser.add_argument("--year", default="2025", help="season year (default: 2025)")
    parser.add_argument(
        "--no-save-fixtures",
        action="store_true",
        help="do not write HTML files to scraper/fixtures (still fetches and loads)",
    )
    args = parser.parse_args()
    team_id = args.team_id
    school_id = args.school_id
    year = args.year

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    from fetch_rendered_html import fetch_one, FIXTURES_DIR
    from run import parse_team_summary, upsert_athletes_marks, get_db

    url = f"https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary"
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    # 1. Fetch all three views in one browser session
    html_by_view = {}
    print(f"Fetching {url} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "ConferenceLeaderboard/1.0 (school use)"})
        for view in ("men", "women", "relays"):
            print(f"  {view} ...")
            html, out_path = fetch_one(page, url, view, team_id, year)
            html_by_view[view] = html
            if not args.no_save_fixtures:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"    saved {len(html)} chars to {os.path.basename(out_path)}")
        browser.close()

    # 2. Parse and upsert all four load steps with one DB connection
    conn = get_db()
    try:
        total_athletes = 0
        for label, (html, gender) in [
            ("men", (html_by_view["men"], "men")),
            ("women", (html_by_view["women"], "women")),
            ("relays (men)", (html_by_view["relays"], "men")),
            ("relays (women)", (html_by_view["relays"], "women")),
        ]:
            athletes = parse_team_summary(html, school_id, gender)
            if athletes:
                upsert_athletes_marks(conn, school_id, gender, athletes)
                total_athletes += len(athletes)
                print(f"  {label}: {len(athletes)} athletes upserted")
            else:
                print(f"  {label}: no athletes parsed")
        print(f"Done. Total athlete records upserted: {total_athletes}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
