#!/usr/bin/env python3
"""
Collect all unique event header labels across all athlete blocks in a fixture.
Usage: python scraper/inspect_all_events.py <path_to.html>
"""
import sys
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bs4 import BeautifulSoup
from run import _event_label_to_slug


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPT_DIR / "fixtures" / "team_summary_12207_2025_women.html"
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    blocks = soup.find_all("div", class_=lambda c: c and "athlete" in (c or "").split())
    label_counts = Counter()
    unmapped = []
    for block in blocks:
        for eh in block.find_all("div", class_=lambda c: c and "event-header" in (c or "").split()):
            raw = (eh.get_text() or "").strip()
            raw = " ".join(raw.split())
            if not raw:
                continue
            label_counts[raw] += 1
            if _event_label_to_slug(raw) is None and raw not in [u[0] for u in unmapped]:
                unmapped.append((raw, 1))
    print("All event labels (raw) and slug:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        slug = _event_label_to_slug(label)
        print(f"  {count:3d}x  {label!r} -> {slug or 'UNMAPPED'}")
    if unmapped:
        print("\nUnmapped labels:", [u[0] for u in unmapped])


if __name__ == "__main__":
    main()
