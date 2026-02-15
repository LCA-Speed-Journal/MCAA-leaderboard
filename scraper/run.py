#!/usr/bin/env python3
"""
Conference Leaderboard scraper.
Fetches athletic.net Team Summary per school (men's + women's), parses athletes/marks, upserts to Neon.
Rate limit: 10–15 s between school requests. User-Agent: ConferenceLeaderboard/1.0.
"""
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Load .env and .env.local from project root so DATABASE_URL is set when run from CLI
_project_root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
    load_dotenv(_project_root / ".env.local", override=True)
except ImportError:
    pass

# Optional: use psycopg2 for local/cron runs; or switch to neon serverless driver if needed
try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

USER_AGENT = "ConferenceLeaderboard/1.0 (school use; contact for removal)"
RATE_LIMIT_SEC = 12
BASE_URL = "https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary"

# Event label (from athletic.net) -> our events.slug (must match events table: 100m–3200m, 110h/100h/300h/60h, 4x100/4x200/4x400/4x800, hj/lj/tj/sp/discus/pv)
EVENT_TO_SLUG = {
    "100m": "100m", "100 m": "100m", "100 meters": "100m",
    "200m": "200m", "200 m": "200m", "200 meters": "200m",
    "400m": "400m", "400 m": "400m", "400 meters": "400m",
    "800m": "800m", "800 m": "800m", "800 meters": "800m",
    "1600m": "1600m", "1600 m": "1600m", "1600": "1600m", "1 mile": "1600m", "mile": "1600m", "1 mile run": "1600m",
    "3200m": "3200m", "3200 m": "3200m", "3200": "3200m", "2 mile": "3200m", "two mile": "3200m", "2 mile run": "3200m",
    "110m hurdles": "110h", "110 m hurdles": "110h", "110 meter hurdles": "110h", "110 meters hurdles": "110h",
    "110mh": "110h", "110 hurdles": "110h",
    "100m hurdles": "100h", "100 m hurdles": "100h", "100 meter hurdles": "100h", "100 meters hurdles": "100h",
    "100mh": "100h", "100 hurdles": "100h",
    "60m hurdles": "60h", "60 m hurdles": "60h", "60 meter hurdles": "60h", "60 meters hurdles": "60h",
    "60mh": "60h", "60 hurdles": "60h",
    "300m hurdles": "300h", "300 m hurdles": "300h", "300 meter hurdles": "300h", "300 meters hurdles": "300h",
    "300mh": "300h", "300 hurdles": "300h",
    "high jump": "hj", "hj": "hj",
    "long jump": "lj", "lj": "lj",
    "triple jump": "tj", "tj": "tj",
    "shot put": "sp", "sp": "sp",
    "discus": "discus", "discus throw": "discus",
    "pole vault": "pv", "pv": "pv",
    "4x100m relay": "4x100", "4x100 relay": "4x100", "4x100": "4x100",
    "4x200m relay": "4x200", "4x200 relay": "4x200", "4x200": "4x200",
    "4x400m relay": "4x400", "4x400 relay": "4x400", "4x400": "4x400",
    "4x800m relay": "4x800", "4x800 relay": "4x800", "4x800": "4x800",
}
# Slugs that are distance (higher is better); rest are time (lower is better)
DISTANCE_SLUGS = {"hj", "lj", "tj", "sp", "discus", "pv"}
# Max plausible value in meters per event (reject marks above these to avoid wrong-event data)
DISTANCE_MAX_METERS = {"hj": 2.5, "pv": 2.5, "lj": 9.0, "tj": 16.0, "sp": 25.0, "discus": 70.0}
# Min plausible (reject place/grade stored as result): shot/discus in meters
DISTANCE_MIN_METERS = {"sp": 5.0, "discus": 15.0}
# Plausible time ranges (seconds) per slug; marks outside are rejected (e.g. place/grade)
TIME_RANGE_SEC = {
    "110h": (12.0, 30.0), "100h": (12.0, 30.0), "60h": (8.0, 15.0),
    "300h": (35.0, 55.0), "100m": (9.0, 25.0), "200m": (18.0, 35.0),
    "400m": (45.0, 75.0), "800m": (100.0, 240.0), "1600m": (210.0, 660.0),  # 3:30–11:00 (allow sub-4 mile)
    "3200m": (480.0, 1200.0),
}


def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set")
    if not psycopg2:
        raise SystemExit("Install psycopg2-binary for scraper DB access")
    return psycopg2.connect(url)


def fetch_schools(conn, conference_id=1):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, athletic_net_team_id, name FROM schools WHERE conference_id = %s",
            (conference_id,),
        )
        return cur.fetchall()


def start_run(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (started_at, status) VALUES (%s, 'running') RETURNING id",
            (datetime.utcnow(),),
        )
        return cur.fetchone()[0]


def finish_run(conn, run_id, status, schools_processed, error_message=None):
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE scrape_runs SET finished_at = %s, status = %s, schools_processed = %s, error_message = %s
               WHERE id = %s""",
            (datetime.utcnow(), status, schools_processed, error_message, run_id),
        )
    conn.commit()


def fetch_page(team_id: str, year: int, gender: str) -> str:
    url = BASE_URL.format(team_id=team_id, year=year)
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def _normalize_event_label(text: str) -> str:
    """Normalize event header/cell to key for EVENT_TO_SLUG lookup."""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text.strip()).lower()
    t = re.sub(r"\s*x\s*", "x", t)
    return t


def _event_label_to_slug(label: str) -> str | None:
    """Map athletic.net event name to our events.slug. Returns None if unknown."""
    key = _normalize_event_label(label)
    if not key:
        return None
    # Strip parenthetical suffix (e.g. " (12 lb)", " (1.6 kg)", " (39\")" ) so other schools' labels match
    key = re.sub(r"\s*\([^)]*\)\s*$", "", key).strip()
    if key in EVENT_TO_SLUG:
        return EVENT_TO_SLUG[key]
    # Try without " meters" / "m " suffix
    for suffix in (" meters", "m"):
        if key.endswith(suffix):
            cand = key[: -len(suffix)].strip()
            if cand in EVENT_TO_SLUG:
                return EVENT_TO_SLUG[cand]
    # Athletic.net appends weight/spec (e.g. " - 12lb", " - 39\" / 0.991m", " - 1.6kg")
    if " - " in key:
        base = key.split(" - ")[0].strip()
        base = re.sub(r"\s*\([^)]*\)\s*$", "", base).strip()
        if base in EVENT_TO_SLUG:
            return EVENT_TO_SLUG[base]
        for suffix in (" meters", "m"):
            if base.endswith(suffix):
                cand = base[: -len(suffix)].strip()
                if cand in EVENT_TO_SLUG:
                    return EVENT_TO_SLUG[cand]
    return None


def _parse_time_to_seconds(s: str) -> float | None:
    """Parse time string to seconds. Handles 10.45, 1:23.45, 4:32."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s or s in ("-", "—", "NT", "DQ", "DNF", "DNS"):
        return None
    s = re.sub(r"\s+", "", s)
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            try:
                return float(parts[0]) * 60 + float(parts[1])
            except ValueError:
                return None
        if len(parts) == 3:
            try:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except ValueError:
                return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_distance_to_meters(s: str, slug: str | None = None) -> float | None:
    """Parse distance to meters. Handles 6.50m, 21-3.5 or 21' 3.5 (feet-inches)."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s or s in ("-", "—", "NH", "ND", "NM"):
        return None
    # Allow space between feet and inches before collapsing
    s_nospace = re.sub(r"\s+", " ", s).strip()
    if s_nospace.endswith("m") and not s_nospace.endswith("mm"):
        try:
            return float(s_nospace[:-1])
        except ValueError:
            pass
    # feet-inches: 21-3.5, 21'3.5", 21' 3.5", 6' 0 (allow optional inch sign at end)
    m = re.match(r"^(\d+)[\-']\s*(\d+(?:\.\d+)?)\s*[\"\u201c\u201d]?$", s_nospace)
    if m:
        try:
            ft, inc = float(m.group(1)), float(m.group(2))
            return ft * 0.3048 + inc * 0.0254
        except ValueError:
            pass
    try:
        val = float(s_nospace)
        # Bare number: if plausibly in feet for jumps/pv, convert (fixes 12 stored as 12m for HJ)
        if slug in ("hj", "pv") and 2.5 < val < 10:
            return val * 0.3048
        if slug in ("lj", "tj") and 9 < val < 30:
            return val * 0.3048
        return val
    except ValueError:
        return None


def _parse_grade(text: str) -> int | None:
    """Parse grade to 9–12 or None. Handles Sr, Jr, Soph, Fr, 10, etc."""
    if not text:
        return None
    t = text.strip().lower()
    if t in ("sr", "12", "senior"):
        return 12
    if t in ("jr", "11", "junior"):
        return 11
    if t in ("soph", "10", "sophomore"):
        return 10
    if t in ("fr", "9", "freshman"):
        return 9
    try:
        g = int(t)
        if 9 <= g <= 12:
            return g
    except ValueError:
        pass
    return None


def _parse_mark_value(s: str, slug: str) -> float | None:
    """Parse a mark cell to numeric value (seconds for time, meters for distance)."""
    if slug in DISTANCE_SLUGS:
        return _parse_distance_to_meters(s, slug)
    return _parse_time_to_seconds(s)


def _parse_date_cell(text: str):
    """Parse date like 4/9/25 or 4/16/25 to (year, month, day) or None."""
    if not text:
        return None
    text = text.strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", text)
    if not m:
        return None
    try:
        month, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3))
        if year < 100:
            year += 2000 if year < 50 else 1900
        if 1 <= month <= 12 and 1 <= day <= 31:
            return (year, month, day)
    except (ValueError, TypeError):
        pass
    return None


def _parse_relay_meet_date(cell, default_year: int = 2025):
    """
    Parse relay table meet cell: contains <a>Meet Name</a><br>Weekday, Mon DD (or space-separated).
    Returns (meet_name, (year, month, day) or None). Uses default_year for the date.
    """
    meet_name = None
    link = cell.find("a") if cell else None
    if link:
        meet_name = (link.get_text() or "").strip()
    raw = (cell.get_text() or "").strip() if cell else ""
    if raw and not meet_name:
        meet_name = raw
    # Parse "Fri, Apr 11", "Thu, May 15", "Mon, Apr 21" anywhere in raw (cell may have newline or space)
    date_tup = None
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\b", raw, re.I)
    if m:
        months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
        try:
            month = months.index(m.group(1).lower()) + 1
            day = int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                date_tup = (default_year, month, day)
        except (ValueError, IndexError):
            pass
    return (meet_name or None, date_tup)


RELAY_SLUGS = {"4x100", "4x200", "4x400", "4x800"}
# When a relay row lists "Relay Team" instead of athlete names, we still store the mark under this placeholder
RELAY_TEAM_PLACEHOLDER_NAME = "Relay Team"


def _parse_athletic_net_relays(soup, gender: str):
    """
    Parse athletic.net Relays tab: sections "Men's Relays" / "Women's Relays",
    each with tables per event (4x100, 4x200, etc.), rows have Place, Result, Round, Members, Meet.
    Returns list of (athlete_name, grade, events_marks). When Members lists four names, each
    athlete gets that mark; when it says "Relay Team" (meet didn't list participants), the
    mark is attributed to a single placeholder athlete "Relay Team" so the time is still stored.
    """
    athletes = []  # (name, grade, events_marks)
    if gender == "men":
        section_label = "Men's Relays"
    else:
        section_label = "Women's Relays"
    section_heading = None
    for tag in ("h4", "h3", "h2"):
        for el in soup.find_all(tag):
            text = (el.get_text() or "").strip().lower()
            if section_label.lower() in text:
                section_heading = el
                break
            if gender == "men" and "men" in text and "relay" in text:
                section_heading = el
                break
            if gender == "women" and "women" in text and "relay" in text:
                section_heading = el
                break
        if section_heading:
            break
    if not section_heading:
        return athletes
    # Infer season year from page (e.g. h2 "2025 Event Progress")
    default_year = 2025
    for el in soup.find_all(["h2", "h3"]):
        txt = (el.get_text() or "") or ""
        ym = re.search(r"\b(20\d{2})\b", txt)
        if ym:
            try:
                default_year = int(ym.group(1))
                break
            except ValueError:
                pass
    section = section_heading.find_parent("div", class_=lambda c: c and "col-" in (c or ""))
    if not section:
        section = section_heading.parent
    tables = section.find_all("table", class_=lambda c: c and "table" in (c or "").split()) if section else []
    if not tables and section:
        tables = section.find_all("table")
    for table in tables:
        thead = table.find("thead")
        if not thead:
            continue
        th = thead.find("th") or thead.find("strong")
        event_label = (th.get_text(strip=True) if th else "") or ""
        slug = _event_label_to_slug(event_label)
        if not slug or slug not in RELAY_SLUGS:
            continue
        tbody = table.find("tbody")
        if not tbody:
            continue
        result_col = _result_column_index(table)
        for tr in tbody.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) <= result_col:
                continue
            result_text = (cells[result_col].get_text() or "").strip()
            value = _parse_mark_value(result_text, slug)
            if value is None:
                continue
            # Members cell (index 3): "Name1\nName2\nName3\nName4" or "Relay Team" (when meet didn't list names)
            members_cell = cells[3]
            names = []
            for br in members_cell.find_all("br"):
                br.replace_with("\n")
            raw = (members_cell.get_text() or "").strip()
            for part in raw.split("\n"):
                name = part.strip()
                if name and name.lower() != "relay team":
                    names.append(name)
            # When no athletes are listed, attribute the mark to a placeholder so we still store it
            if not names:
                names = [RELAY_TEAM_PLACEHOLDER_NAME]
            mark_date = None
            meet_name = None
            if len(cells) >= 5:
                meet_name, date_tup = _parse_relay_meet_date(cells[4], default_year)
                if date_tup:
                    mark_date = datetime(*date_tup).date()
            for name in names:
                athletes.append((name, None, [(slug, value, mark_date, meet_name)]))
    # Merge by athlete name so we return one (name, grade, events_marks) per person
    by_name = {}
    for name, grade, events_marks in athletes:
        if name not in by_name:
            by_name[name] = (name, grade, [])
        by_name[name][2].extend(events_marks)
    return list(by_name.values())


def _is_marks_table(table) -> bool:
    """
    True if this is the per-meet marks table (Place, Result, Date, Meet; or with Wind/Round).
    False if it is the summary table (Season, Grade, Best Result).
    """
    thead = table.find("thead")
    tbody = table.find("tbody")
    if not tbody:
        return False
    first_row = tbody.find("tr")
    if not first_row or len(first_row.find_all(["td", "th"])) < 4:
        return False
    if not thead:
        return True  # No thead but 5+ columns: treat as per-meet table
    headers = [ (th.get_text() or "").strip().lower() for th in thead.find_all(["th", "td"]) ]
    # Summary table has exactly Season, Grade, Best Result — skip it for _is_marks_table
    if len(headers) == 3:
        if "season" in headers and "grade" in headers and "best" in " ".join(headers):
            return False
    return True


def _is_summary_best_table(table) -> bool:
    """True if this is the 3-col summary table (Season, Grade, Best Result). We can use col 2 for best mark."""
    thead = table.find("thead") if table else None
    tbody = table.find("tbody") if table else None
    if not tbody or not tbody.find("tr"):
        return False
    first_row = tbody.find("tr")
    if len(first_row.find_all(["td", "th"])) != 3:
        return False
    if not thead:
        return True
    headers = [(th.get_text() or "").strip().lower() for th in thead.find_all(["th", "td"])]
    if len(headers) != 3:
        return False
    joined = " ".join(headers)
    return ("best" in joined or "result" in joined or "mark" in joined) and ("season" in joined or "grade" in joined or "best" in joined)


def _result_column_index(table) -> int:
    """Return column index for Result/Mark from thead; default 1 (Place, Result, ...)."""
    thead = table.find("thead") if table else None
    if not thead:
        return 1
    for i, th in enumerate(thead.find_all(["th", "td"])):
        text = ((th.get_text() or "").strip().lower())
        if "result" in text or ("mark" in text and "best" not in text) or "time" in text or "distance" in text:
            return i
    return 1


def _parse_athletic_net_angular(soup):
    """
    Parse athletic.net full-season team page: one div.athlete per athlete,
    each with athlete-header (name, grade) and per-event tables (Place, Result, Date, Meet).
    Returns list of (athlete_name, grade, events_marks).
    """
    athletes = []
    # Angular: div with class "athlete" containing athlete-header + event sections with tables
    athlete_blocks = soup.find_all("div", class_=lambda c: c and "athlete" in c.split())
    for block in athlete_blocks:
        header = block.find("div", class_=lambda c: c and "athlete-header" in c.split())
        if not header:
            continue
        link = header.find("a", href=re.compile(r"/athlete/"))
        name = (link.get_text(strip=True) if link else header.get_text(strip=True)) or ""
        if not name:
            continue
        small = header.find("small")
        grade_text = (small.get_text(strip=True) if small else "") or ""
        grade = _parse_grade(grade_text.replace("th Grade", "").replace("st", "").replace("nd", "").replace("rd", "").strip())
        events_marks = []
        event_headers_list = block.find_all("div", class_=lambda c: c and "event-header" in (c or "").split())
        for idx, event_header in enumerate(event_headers_list):
            event_label_el = event_header.find(["strong", "span", "a"])
            event_label = (event_header.get_text() or event_label_el.get_text() if event_label_el else "") or ""
            slug = _event_label_to_slug(event_label)
            if not slug:
                continue
            # Use a table for this event: first table after this header with prev_h == event_header (marks or summary).
            # Try several candidates so other schools with multiple tables (e.g. summary + marks) still match.
            table = None
            candidate = event_header.find_next("table")
            for _ in range(6):
                if not candidate or not candidate.find("tbody"):
                    break
                prev_h = candidate.find_previous("div", class_=lambda c: c and "event-header" in (c or "").split())
                if prev_h == event_header:
                    if _is_marks_table(candidate):
                        table = candidate
                        break
                    if _is_summary_best_table(candidate):
                        table = candidate
                        break
                candidate = candidate.find_next("table")
            if not table:
                tables_in_block = [
                    t for t in block.find_all("table")
                    if t.find("tbody") and (_is_marks_table(t) or _is_summary_best_table(t))
                ]
                if idx < len(tables_in_block):
                    table = tables_in_block[idx]
            if not table:
                continue
            tbody = table.find("tbody")
            if not tbody:
                continue
            result_col = _result_column_index(table) if not _is_summary_best_table(table) else 2
            # Columns: 6-col = Place, Result, Wind, Round, Date, Meet (0-5); 4-col = Place, Result, Date, Meet (0-3); 3-col summary = Season, Grade, Best Result (col 2)
            for tr in tbody.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) <= result_col:
                    continue
                result_text = (cells[result_col].get_text() or "").strip()
                value = _parse_mark_value(result_text, slug)
                if value is None:
                    continue
                if slug in DISTANCE_SLUGS:
                    max_m = DISTANCE_MAX_METERS.get(slug)
                    if max_m is not None and value > max_m:
                        continue
                    min_m = DISTANCE_MIN_METERS.get(slug)
                    if min_m is not None and value < min_m:
                        continue
                if slug in TIME_RANGE_SEC:
                    lo, hi = TIME_RANGE_SEC[slug]
                    if value < lo or value > hi:
                        continue
                date_idx = 4 if len(cells) >= 6 else 2
                meet_idx = 5 if len(cells) >= 6 else 3
                date_tup = None
                if len(cells) > date_idx:
                    date_tup = _parse_date_cell((cells[date_idx].get_text() or "").strip())
                mark_date = datetime(*date_tup).date() if date_tup else None
                meet_name = None
                if len(cells) > meet_idx:
                    meet_cell = cells[meet_idx]
                    link = meet_cell.find("a")
                    meet_name = (link.get_text() or meet_cell.get_text() or "").strip() or None
                events_marks.append((slug, value, mark_date, meet_name))
        if events_marks:
            athletes.append((name, grade, events_marks))
    return athletes


def parse_team_summary(html: str, school_id: int, gender: str):
    """
    Parse Team Summary HTML. Returns list of (athlete_name, grade, events_marks)
    where events_marks is list of (event_slug, value, mark_date).
    Supports (1) athletic.net Angular layout: div.athlete blocks with per-event tables;
    (2) single table with thead event columns and one row per athlete.
    """
    soup = BeautifulSoup(html, "lxml")
    # Try Angular layout first (athlete blocks with event-header + table per event)
    athletes = _parse_athletic_net_angular(soup)
    if athletes:
        return athletes

    # Relays tab: Men's Relays / Women's Relays sections with tables per event (no div.athlete)
    athletes = _parse_athletic_net_relays(soup, gender)
    if athletes:
        return athletes

    # Fallback: single table with thead (event columns) and tbody (one row per athlete)
    tables = soup.find_all("table")
    data_rows = []
    for t in tables:
        tbody = t.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            if rows:
                data_rows.extend(rows)
    if not data_rows:
        return []

    main_table = None
    for t in tables:
        thead = t.find("thead")
        tbody = t.find("tbody")
        if thead and tbody:
            ths = thead.find_all(["th", "td"])
            trs = tbody.find_all("tr")
            if ths and len(trs) >= 1:
                main_table = (t, ths, trs)
                break
    if not main_table:
        return []

    table, header_cells, body_rows = main_table
    col_to_slug = {}
    name_col = 0
    grade_col = None
    for i, cell in enumerate(header_cells):
        label = (cell.get_text() or "").strip()
        slug = _event_label_to_slug(label)
        if slug:
            col_to_slug[i] = slug
        else:
            label_lower = label.lower()
            if "athlete" in label_lower or "name" in label_lower:
                name_col = i
            elif "grade" in label_lower or "yr" == label_lower or label in ("9", "10", "11", "12"):
                grade_col = i

    if not col_to_slug:
        return []

    for tr in body_rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) <= name_col:
            continue
        name_el = cells[name_col]
        name_link = name_el.find("a")
        name = (name_link.get_text(strip=True) if name_link else name_el.get_text(strip=True)) or ""
        if not name or name.lower() in ("athlete", "name"):
            continue
        grade = _parse_grade(cells[grade_col].get_text(strip=True)) if grade_col is not None and grade_col < len(cells) else None
        events_marks = []
        for i, slug in col_to_slug.items():
            if i >= len(cells):
                continue
            raw = (cells[i].get_text() or "").strip()
            val = _parse_mark_value(raw, slug)
            if val is not None:
                events_marks.append((slug, val, None))
        if events_marks:
            athletes.append((name, grade, events_marks))

    return athletes


def upsert_athletes_marks(conn, school_id: int, gender: str, athletes: list):
    if not athletes:
        return
    gender_char = "M" if gender == "men" else "F"
    with conn.cursor() as cur:
        for name, grade, events_marks in athletes:
            cur.execute(
                """INSERT INTO athletes (school_id, name, grade, gender)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (school_id, name, grade, gender) DO UPDATE SET name = athletes.name
                   RETURNING id""",
                (school_id, name, grade or None, gender_char),
            )
            row = cur.fetchone()
            if not row:
                continue
            athlete_id = row[0]
            for item in events_marks:
                if len(item) == 4:
                    event_slug, value, mark_date, meet_name = item
                else:
                    event_slug, value, mark_date = item
                    meet_name = None
                cur.execute("SELECT id FROM events WHERE slug = %s", (event_slug,))
                ev = cur.fetchone()
                if not ev:
                    continue
                if event_slug in DISTANCE_SLUGS:
                    max_m = DISTANCE_MAX_METERS.get(event_slug)
                    if max_m is not None and float(value) > max_m:
                        continue
                event_id = ev[0]
                cur.execute(
                    """INSERT INTO marks (athlete_id, event_id, value, mark_date, meet_name)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (athlete_id, event_id, mark_date, value) DO UPDATE SET meet_name = EXCLUDED.meet_name""",
                    (athlete_id, event_id, value, mark_date, meet_name),
                )
    conn.commit()


def main():
    year = int(os.environ.get("SEASON_YEAR", "2026"))
    conference_id = int(os.environ.get("CONFERENCE_ID", "1"))

    conn = get_db()
    run_id = start_run(conn)
    conn.commit()

    schools = fetch_schools(conn, conference_id)
    processed = 0
    err_msg = None
    try:
        for school_id, team_id, name in schools:
            for gender in ("men", "women"):
                try:
                    html = fetch_page(team_id, year, gender)
                    athletes = parse_team_summary(html, school_id, gender)
                    upsert_athletes_marks(conn, school_id, gender, athletes)
                except Exception as e:
                    err_msg = str(e)
                    # continue with next school/gender
                time.sleep(RATE_LIMIT_SEC)
            processed += 1
        finish_run(conn, run_id, "success", processed)
    except Exception as e:
        finish_run(conn, run_id, "failed", processed, str(e))
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
