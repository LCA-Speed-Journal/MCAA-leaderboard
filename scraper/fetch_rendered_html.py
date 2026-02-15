#!/usr/bin/env python3
"""
Fetch athletic.net Team Summary with a headless browser so the full DOM is rendered
(Angular loads content via JS). Saves HTML to scraper/fixtures/ for parsing.

The page has Men / Women / Relays tabs (default Men). Pass view to fetch the correct tab.

Usage:
  python scraper/fetch_rendered_html.py [team_id] [year] [view]
  Default: team_id=73442, year=2025, view=men
  view: men | women | relays | all  (all = fetch men, women, and relays; saves three files)

Requires: pip install playwright && python -m playwright install chromium
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

def fetch_one(page, url: str, view: str, team_id: str, year: str) -> tuple[str, str]:
    """Load url, optionally switch to Women or Relays tab, return (html, output_path)."""
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector("table, [class*='table'], .athlete", timeout=15000)
    except Exception:
        page.wait_for_timeout(3000)
    if view == "women":
        try:
            page.locator("a.nav-link").filter(has_text="Women").first.click(timeout=5000)
            page.wait_for_timeout(2000)
            page.wait_for_selector(".athlete", timeout=10000)
        except Exception as e:
            print(f"Warning: could not switch to Women tab: {e}")
    elif view == "relays":
        try:
            page.locator("a.nav-link").filter(has_text="Relays").first.click(timeout=5000)
            page.wait_for_timeout(2000)
            page.wait_for_selector("table, .athlete", timeout=10000)
        except Exception as e:
            print(f"Warning: could not switch to Relays tab: {e}")
    html = page.content()
    if view == "women":
        out_name = f"team_summary_{team_id}_{year}_women.html"
    elif view == "relays":
        out_name = f"team_summary_{team_id}_{year}_relays.html"
    else:
        out_name = f"team_summary_{team_id}_{year}.html"
    out_path = os.path.join(FIXTURES_DIR, out_name)
    return html, out_path


def main():
    team_id = sys.argv[1] if len(sys.argv) > 1 else "73442"
    year = sys.argv[2] if len(sys.argv) > 2 else "2025"
    view = (sys.argv[3] if len(sys.argv) > 3 else "men").lower()
    if view not in ("men", "women", "relays", "all"):
        print("view must be: men | women | relays | all")
        sys.exit(1)
    url = f"https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    to_fetch = ["men", "women", "relays"] if view == "all" else [view]
    print(f"Loading {url} ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "ConferenceLeaderboard/1.0 (school use)"})
        for v in to_fetch:
            print(f"  Fetching {v} ...")
            html, out_path = fetch_one(page, url, v, team_id, year)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Saved {len(html)} chars to {out_path}")
        browser.close()


if __name__ == "__main__":
    main()
