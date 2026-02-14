#!/usr/bin/env python3
"""
Conference Leaderboard scraper.
Fetches athletic.net Team Summary per school (men's + women's), parses athletes/marks, upserts to Neon.
Rate limit: 10–15 s between school requests. User-Agent: ConferenceLeaderboard/1.0.
"""
import os
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Optional: use psycopg2 for local/cron runs; or switch to neon serverless driver if needed
try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

USER_AGENT = "ConferenceLeaderboard/1.0 (school use; contact for removal)"
RATE_LIMIT_SEC = 12
BASE_URL = "https://www.athletic.net/team/{team_id}/track-and-field-outdoor/{year}/team-summary"


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


def parse_team_summary(html: str, school_id: int, gender: str):
    """
    Parse Team Summary HTML. Returns list of (athlete_name, grade, events_marks)
    where events_marks is list of (event_slug_or_name, value, mark_date).
    Defensive: normalize event names to match events.slug where possible.
    """
    soup = BeautifulSoup(html, "lxml")
    athletes = []
    # athletic.net structure varies; placeholder selectors - replace with real selectors
    # after inspecting sample HTML. Example placeholder:
    # for row in soup.select("table.team-summary tbody tr"):
    #   name = row.select_one(".athlete-name")
    #   ...
    # For MVP we add no rows if structure is unknown; scraper still runs and records run.
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
            for event_slug, value, mark_date in events_marks:
                cur.execute("SELECT id FROM events WHERE slug = %s", (event_slug,))
                ev = cur.fetchone()
                if not ev:
                    continue
                event_id = ev[0]
                cur.execute(
                    """INSERT INTO marks (athlete_id, event_id, value, mark_date)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (athlete_id, event_id, mark_date, value) DO NOTHING""",
                    (athlete_id, event_id, value, mark_date),
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
