#!/usr/bin/env python3
"""
Diagnostic: compare parser output across schools to find why some events
only show Liberty marks. Run from project root with fixtures present.

Usage: python scraper/diagnose_parser.py [--verbose]
"""
import os
import sys
from pathlib import Path
from collections import defaultdict

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

# School label by team_id (from seed)
TEAM_LABELS = {
    "73442": "Liberty",
    "12529": "Eagle Ridge",
    "12207": "CHOF",
    "12079": "MSA",
    "12454": "Mayer Lutheran",
    "34824": "NLA/LILA",
    "75792": "Parnassus",
    "38174": "Spectrum",
    "12356": "West Lutheran",
}

# Events user said are affected (both genders: throws, 1600m, hurdles)
FOCUS_SLUGS = {"1600m", "100h", "110h", "sp", "discus", "100m", "800m", "4x100", "hj"}


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    fixtures_dir = SCRIPT_DIR / "fixtures"

    from run import parse_team_summary

    # Men's: team_summary_<team_id>_2025.html (no _women, no _relays)
    men_files = sorted(fixtures_dir.glob("team_summary_*_2025.html"))
    men_files = [f for f in men_files if not f.name.endswith("_women.html") and "_relays" not in f.name]
    # Women's: team_summary_<team_id>_2025_women.html
    women_files = sorted(fixtures_dir.glob("team_summary_*_2025_women.html"))

    if not men_files:
        print("No men's fixtures found. Run fetch_rendered_html or sync_conference first.")
        sys.exit(1)

    print("=== Parser diagnostic: per-school event counts (MEN) ===\n")

    for path in men_files:
        # team_summary_73442_2025.html -> 73442
        name = path.stem.replace("team_summary_", "").replace("_2025", "")
        team_id = name.split("_")[0] if name else "?"
        label = TEAM_LABELS.get(team_id, team_id)

        with open(path, encoding="utf-8") as f:
            html = f.read()
        athletes = parse_team_summary(html, school_id=1, gender="men")
        if not athletes:
            print(f"{label} ({team_id}): 0 athletes parsed")
            continue

        by_slug = defaultdict(int)
        for _name, _grade, events_marks in athletes:
            for slug, _val, *_ in events_marks:
                by_slug[slug] += 1

        focus = {s: by_slug.get(s, 0) for s in FOCUS_SLUGS}
        print(f"{label} ({team_id}): {len(athletes)} athletes, marks by event:")
        for slug in sorted(FOCUS_SLUGS):
            count = focus[slug]
            mark = "  OK" if count else "  MISSING"
            print(f"  {slug}: {count}{mark}")
        if verbose:
            all_slugs = sorted(by_slug.keys())
            print(f"  All slugs: {all_slugs}")
        print()

    if women_files:
        print("=== Parser diagnostic: per-school event counts (WOMEN) ===\n")
        for path in women_files:
            name = path.stem.replace("team_summary_", "").replace("_2025_women", "")
            team_id = name.split("_")[0] if name else "?"
            label = TEAM_LABELS.get(team_id, team_id)
            with open(path, encoding="utf-8") as f:
                html = f.read()
            athletes = parse_team_summary(html, school_id=1, gender="women")
            if not athletes:
                print(f"{label} ({team_id}): 0 athletes parsed")
                continue
            by_slug = defaultdict(int)
            for _name, _grade, events_marks in athletes:
                for slug, _val, *_ in events_marks:
                    by_slug[slug] += 1
            focus = {s: by_slug.get(s, 0) for s in FOCUS_SLUGS}
            print(f"{label} ({team_id}): {len(athletes)} athletes, marks by event:")
            for slug in sorted(FOCUS_SLUGS):
                count = focus[slug]
                mark = "  OK" if count else "  MISSING"
                print(f"  {slug}: {count}{mark}")
            print()

    print("=== Done ===")


if __name__ == "__main__":
    main()
