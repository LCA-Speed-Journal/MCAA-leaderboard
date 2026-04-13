#!/usr/bin/env python3
"""
Remove marks dated before Jan 1 of the given season year, then delete athletes with no marks.

Default year=2026 removes 2025-and-earlier meet dates from Neon so the leaderboard reflects
the current outdoor season after you re-sync with --year 2026.

Usage (from project root; DATABASE_URL in .env / .env.local):
  python scraper/clear_marks_before_year.py
  python scraper/clear_marks_before_year.py --year 2026
"""
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local", override=True)
except ImportError:
    pass

from run import get_db  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Delete marks before Jan 1 of season year.")
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Keep marks with mark_date on or after Jan 1 of this year (default: 2026)",
    )
    args = parser.parse_args()
    cutoff = f"{args.year}-01-01"

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM marks WHERE mark_date IS NOT NULL AND mark_date < %s::date",
                (cutoff,),
            )
            deleted_marks = cur.rowcount
            cur.execute(
                "DELETE FROM athletes a WHERE NOT EXISTS (SELECT 1 FROM marks m WHERE m.athlete_id = a.id)"
            )
            deleted_athletes = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted_marks} mark(s) with mark_date before {cutoff}.")
        print(f"Deleted {deleted_athletes} athlete row(s) with no marks remaining.")
        print("Re-sync 2026 data if needed: python scraper/sync_conference.py --year 2026")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
