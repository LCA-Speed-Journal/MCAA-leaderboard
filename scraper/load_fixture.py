#!/usr/bin/env python3
"""
Load a saved team-summary HTML file into the database (parse + upsert).
Use after fetch_rendered_html.py to push fixture data to Neon.

Usage (from project root; DATABASE_URL in .env.local):
  python scraper/load_fixture.py <path_to.html> <school_id> <gender>

Example (Liberty Classical Academy, school_id 1, men):
  python scraper/load_fixture.py scraper/fixtures/team_summary_73442_2025.html 1 men
"""
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
    if len(sys.argv) < 4:
        print("Usage: python scraper/load_fixture.py <path_to.html> <school_id> <gender>")
        print("  gender: men | women")
        sys.exit(1)
    path = sys.argv[1]
    school_id = int(sys.argv[2])
    gender = sys.argv[3].lower()
    if gender not in ("men", "women"):
        print("gender must be 'men' or 'women'")
        sys.exit(1)
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    from run import parse_team_summary, upsert_athletes_marks, get_db
    athletes = parse_team_summary(html, school_id, gender)
    print(f"Parsed {len(athletes)} athletes")
    if not athletes:
        sys.exit(0)
    conn = get_db()
    try:
        upsert_athletes_marks(conn, school_id, gender, athletes)
        print("Upserted to database.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
