#!/usr/bin/env python3
"""
Run the parser on a saved HTML file (e.g. from fetch_rendered_html.py or browser "Save as").
Usage: python scraper/parse_sample.py [path_to.html]
        If no path given, tries scraper/fixtures/team_summary_73442_2025.html
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(SCRIPT_DIR, "fixtures", "team_summary_73442_2025.html")
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        print("Run: python scraper/fetch_rendered_html.py 73442 2025")
        print("  or pass a path to saved team summary HTML.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    from run import parse_team_summary
    athletes = parse_team_summary(html, school_id=1, gender="men")
    print(f"Parsed {len(athletes)} athletes from {path}")
    for name, grade, events_marks in athletes[:10]:
        print(f"  {name} (grade {grade}): {len(events_marks)} marks")
    if len(athletes) > 10:
        print(f"  ... and {len(athletes) - 10} more")

if __name__ == "__main__":
    main()
