#!/usr/bin/env python3
"""
Inspect event headers and slug resolution in team-summary HTML.
Use to compare Liberty vs other schools when some events fail to parse.

Usage: python scraper/inspect_event_headers.py <path_to.html>
Example: python scraper/inspect_event_headers.py scraper/fixtures/team_summary_12207_2025.html
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bs4 import BeautifulSoup

# Import just the slug resolver
from run import _event_label_to_slug


def main():
    if len(sys.argv) < 2:
        print("Usage: python scraper/inspect_event_headers.py <path_to.html>")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        sys.exit(1)
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    athlete_blocks = soup.find_all("div", class_=lambda c: c and "athlete" in (c or "").split())
    print(f"Found {len(athlete_blocks)} div.athlete blocks\n")

    if not athlete_blocks:
        print("No athlete blocks — page may use different layout (relays or single table).")
        sys.exit(0)

    # Inspect first athlete block only (same structure for all)
    block = athlete_blocks[0]
    header = block.find("div", class_=lambda c: c and "athlete-header" in (c or "").split())
    name = "?"
    if header:
        link = header.find("a", href=lambda h: h and "/athlete/" in h)
        name = (link.get_text(strip=True) if link else header.get_text(strip=True)) or "?"
    print(f"First athlete: {name}\n")

    event_headers = block.find_all("div", class_=lambda c: c and "event-header" in (c or "").split())
    print(f"Event headers in first block: {len(event_headers)}\n")
    print("Label (raw) -> slug")
    print("-" * 50)
    for i, eh in enumerate(event_headers):
        label_el = eh.find(["strong", "span", "a"])
        raw = (eh.get_text() or (label_el.get_text() if label_el else "")) or ""
        raw_stripped = " ".join(raw.split())
        slug = _event_label_to_slug(raw)
        status = slug if slug else "UNMAPPED"
        print(f"  [{i}] {raw_stripped!r} -> {status}")

    tables = block.find_all("table")
    tbody_tables = [t for t in tables if t.find("tbody")]
    print(f"\nTables in first block: {len(tables)} (with tbody: {len(tbody_tables)})")
    print("Done.")


if __name__ == "__main__":
    main()
