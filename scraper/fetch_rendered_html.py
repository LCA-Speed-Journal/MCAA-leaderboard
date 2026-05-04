#!/usr/bin/env python3
"""
Fetch athletic.net Team Summary with a headless browser so the full DOM is rendered
(Angular loads content via JS). Saves HTML to scraper/fixtures/ for parsing.

The page has Men / Women / Relays tabs (default Men). Pass view to fetch the correct tab.

Usage:
  python scraper/fetch_rendered_html.py [team_id] [year] [view]
  Default: team_id=73442, year=2026, view=men
  view: men | women | relays | all  (all = fetch men, women, and relays; saves three files)

Requires: pip install playwright && python -m playwright install chromium
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(SCRIPT_DIR, "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

# athletic.net serves Angular team summary with Men / Women / Relays as a.nav-link.
# Tabs can appear many seconds after navigation (title may change e.g. to "Full Season Team: …").
# Poll in chunks so we can fail fast on Cloudflare titles instead of waiting 120s+90s per view.
# Tab anchors include a gender icon + text; use whitespace-tolerant regexes on clicks.
_TAB_POLL_CHUNK_MS = 25_000
_TAB_POLL_MAX_CHUNKS = 8
_TAB_CLICK_TIMEOUT_MS = 25_000
_POST_TAB_SETTLE_MS = 2500
_POST_GOTO_SETTLE_MS = 2000

_JS_GENDER_TABS_READY = """() => {
  const texts = [...document.querySelectorAll('a.nav-link')].map(
    (a) => (a.textContent || '').trim()
  );
  return texts.includes('Men') && texts.includes('Women') && texts.includes('Relays');
}"""

# Tab anchors include a gender icon + text; textContent is e.g. " Women " not "Women".
_RE_TAB_WOMEN = re.compile(r"^\s*Women\s*$", re.I)
_RE_TAB_RELAYS = re.compile(r"^\s*Relays\s*$", re.I)


def _click_team_summary_tab(page, pattern: re.Pattern[str]) -> None:
    _dismiss_blocking_ui(page)
    tab = page.locator("a.nav-link").filter(has_text=pattern).first
    tab.scroll_into_view_if_needed()
    try:
        tab.click(timeout=_TAB_CLICK_TIMEOUT_MS)
    except Exception:
        _dismiss_blocking_ui(page)
        tab.scroll_into_view_if_needed()
        tab.click(timeout=_TAB_CLICK_TIMEOUT_MS, force=True)


def _try_dismiss_overlays(page) -> None:
    """Cookie / consent UI can intercept clicks on the gender tabs."""
    for sel in ('button.agree-button:has-text("I Agree")', 'button:has-text("I Agree")'):
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=800):
                btn.click(timeout=5000)
                page.wait_for_timeout(600)
                break
        except Exception:
            pass


def _try_dismiss_modals(page) -> None:
    """ng-bootstrap dialogs (e.g. promos) sit above tabs and block clicks on women/relays."""
    try:
        modal = page.locator("ngb-modal-window.modal.show").first
        if modal.is_visible(timeout=600):
            for sel in (
                "ngb-modal-window.modal.show button.close",
                "ngb-modal-window.modal.show .modal-header button",
                'ngb-modal-window.modal.show button:has-text("Close")',
            ):
                try:
                    page.locator(sel).first.click(timeout=4000)
                    page.wait_for_timeout(500)
                    break
                except Exception:
                    continue
            else:
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                except Exception:
                    pass
    except Exception:
        pass


def _dismiss_blocking_ui(page) -> None:
    """Anything that commonly blocks tab clicks after the summary has loaded."""
    _try_dismiss_overlays(page)
    _try_dismiss_modals(page)
    _try_dismiss_overlays(page)


def _title_blocks_sync(title: str) -> bool:
    """Document title patterns seen on Cloudflare / bot interstitials (not team summary)."""
    if not title:
        return False
    tl = title.lower()
    return (
        "cloudflare" in tl
        or "attention required" in tl
        or "just a moment" in tl
    )


def _raise_if_blocked_page(page) -> None:
    try:
        t = page.title()
    except Exception:
        return
    if _title_blocks_sync(t):
        raise RuntimeError(
            "athletic.net is showing a Cloudflare / anti-bot page instead of team summary "
            f"(title={t!r}). Try again later, increase delay between schools, or use a different network."
        )


def _wait_summary_ready(page) -> None:
    """Wait until Men/Women/Relays tabs exist (Angular + any blocking modal settled)."""
    _dismiss_blocking_ui(page)
    for chunk_i in range(_TAB_POLL_MAX_CHUNKS):
        _raise_if_blocked_page(page)
        try:
            page.wait_for_function(_JS_GENDER_TABS_READY, timeout=_TAB_POLL_CHUNK_MS)
            break
        except Exception:
            _raise_if_blocked_page(page)
            if chunk_i in (2, 5):
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                _dismiss_blocking_ui(page)
    else:
        title = ""
        u = ""
        try:
            title = page.title()
            u = page.url
        except Exception:
            pass
        raise TimeoutError(
            "Team summary Men/Women/Relays tabs did not appear in time "
            f"({(_TAB_POLL_CHUNK_MS * _TAB_POLL_MAX_CHUNKS) // 1000}s). "
            f"title={title!r} url={u!r}"
        ) from None

    _raise_if_blocked_page(page)

    # Default view is Men: wait for athlete rows when present (roster can be empty).
    try:
        page.wait_for_selector(".athlete", timeout=20_000)
    except Exception:
        pass


def fetch_one(page, url: str, view: str, team_id: str, year: str) -> tuple[str, str]:
    """Load url, optionally switch to Women or Relays tab, return (html, output_path)."""
    url_norm = url.rstrip("/")
    try:
        current = page.url.rstrip("/")
    except Exception:
        current = ""
    # Reloading the same team-summary URL three times in a row (men → women → relays) often
    # leaves the second/third navigation without tab markup (rate limiting / partial shell). One
    # goto per school, then tab clicks, matches a normal user and is much more reliable.
    skip_goto = view != "men" and current == url_norm
    if skip_goto:
        try:
            if not page.evaluate(_JS_GENDER_TABS_READY):
                skip_goto = False
        except Exception:
            skip_goto = False

    if not skip_goto:
        # `load` can fire before Angular paints tabs on some teams; domcontentloaded + settle + wait_for_function is safer.
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(_POST_GOTO_SETTLE_MS)
    _wait_summary_ready(page)

    if view == "women":
        try:
            _click_team_summary_tab(page, _RE_TAB_WOMEN)
            page.wait_for_timeout(_POST_TAB_SETTLE_MS)
            page.wait_for_selector(".athlete", timeout=20_000)
        except Exception as e:
            print(f"Warning: could not switch to Women tab: {e}")
    elif view == "relays":
        try:
            _click_team_summary_tab(page, _RE_TAB_RELAYS)
            page.wait_for_timeout(_POST_TAB_SETTLE_MS)
            page.wait_for_selector("table, .athlete", timeout=20_000)
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
    year = sys.argv[2] if len(sys.argv) > 2 else "2026"
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
