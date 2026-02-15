import { NextRequest, NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

type Mode = "pr" | "avg3";
type Gender = "men" | "women";

const genderMap: Record<Gender, string> = { men: "M", women: "F" };
const RELAY_SLUGS = ["4x100", "4x200", "4x400", "4x800"];

/** Correct values that were stored as feet instead of meters (e.g. 12 for HJ). Only convert when value is above plausible meters. */
function sanitizeDistanceValue(slug: string, value: number): number {
  const v = Number(value);
  if (slug === "hj" || slug === "pv") {
    if (v > 2.5 && v < 10) return v * 0.3048; // feet -> meters
  }
  if (slug === "lj") {
    if (v > 9.5) return v * 0.3048; // plausible LJ meters ≤ ~9m; 10+ likely feet
  }
  if (slug === "tj") {
    if (v > 16) return v * 0.3048; // plausible TJ meters ≤ ~16m; 17+ likely feet
  }
  return v;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const eventSlug = searchParams.get("event");
  const gender = searchParams.get("gender") as Gender | null;
  const mode = (searchParams.get("mode") as Mode) || "pr";

  if (!eventSlug || !gender) {
    return NextResponse.json(
      { error: "Query params 'event' and 'gender' are required" },
      { status: 400 }
    );
  }
  if (gender !== "men" && gender !== "women") {
    return NextResponse.json(
      { error: "gender must be 'men' or 'women'" },
      { status: 400 }
    );
  }
  if (mode !== "pr" && mode !== "avg3") {
    return NextResponse.json(
      { error: "mode must be 'pr' or 'avg3'" },
      { status: 400 }
    );
  }

  const genderChar = genderMap[gender];
  const sql = getSql();
  const isRelay = RELAY_SLUGS.includes(eventSlug);

  try {
    if (mode === "pr" && isRelay) {
      const rows = await sql`
        WITH school_best AS (
          SELECT s.id, s.name AS school_name, MIN(m.value) AS value
          FROM marks m
          JOIN athletes a ON a.id = m.athlete_id
          JOIN schools s ON s.id = a.school_id
          JOIN events e ON e.id = m.event_id
          WHERE e.slug = ${eventSlug}
            AND a.gender = ${genderChar}
          GROUP BY s.id, s.name
        )
        SELECT
          ROW_NUMBER() OVER (ORDER BY value ASC NULLS LAST)::int AS rank,
          'Relay' AS athlete_name,
          school_name,
          value
        FROM school_best
        ORDER BY rank
      `;
      return NextResponse.json(
        { mode: "pr", rows },
        { headers: { "Cache-Control": "no-store, max-age=0" } }
      );
    }

    if (mode === "pr") {
      const rows = await sql`
        WITH best_marks AS (
          SELECT
            s.id AS school_id,
            a.name AS athlete_name,
            s.name AS school_name,
            e.better_direction,
            CASE
              WHEN e.better_direction = 'lower' THEN MIN(m.value)
              ELSE MAX(m.value)
            END AS value
          FROM marks m
          JOIN athletes a ON a.id = m.athlete_id
          JOIN schools s ON s.id = a.school_id
          JOIN events e ON e.id = m.event_id
          WHERE e.slug = ${eventSlug}
            AND a.gender = ${genderChar}
            AND a.name != 'Relay Team'
          GROUP BY s.id, s.name, a.name, e.better_direction
        )
        SELECT
          ROW_NUMBER() OVER (
            PARTITION BY better_direction
            ORDER BY
              CASE WHEN better_direction = 'lower' THEN value END ASC NULLS LAST,
              CASE WHEN better_direction = 'higher' THEN value END DESC NULLS LAST
          )::int AS rank,
          athlete_name,
          school_name,
          value
        FROM best_marks
        ORDER BY rank
      `;
      const sanitized = (rows as { rank: number; athlete_name: string; school_name: string; value: number }[]).map(
        (r) => ({ ...r, value: sanitizeDistanceValue(eventSlug, r.value) })
      );
      return NextResponse.json(
        { mode: "pr", rows: sanitized },
        { headers: { "Cache-Control": "no-store, max-age=0" } }
      );
    }

    if (mode === "avg3" && isRelay) {
      const rows = await sql`
        WITH school_performances AS (
          SELECT DISTINCT s.id, s.name AS school_name, m.mark_date, m.value
          FROM marks m
          JOIN athletes a ON a.id = m.athlete_id
          JOIN schools s ON s.id = a.school_id
          JOIN events e ON e.id = m.event_id
          WHERE e.slug = ${eventSlug}
            AND a.gender = ${genderChar}
        ),
        ranked AS (
          SELECT id, school_name, value,
            ROW_NUMBER() OVER (PARTITION BY id ORDER BY mark_date DESC NULLS LAST) AS rn
          FROM school_performances
        ),
        last_three AS (
          SELECT id, school_name, AVG(value) AS value
          FROM ranked
          WHERE rn <= 3
          GROUP BY id, school_name
        )
        SELECT
          ROW_NUMBER() OVER (ORDER BY value ASC NULLS LAST)::int AS rank,
          'Relay' AS athlete_name,
          school_name,
          ROUND(value::numeric, 2) AS value
        FROM last_three
        ORDER BY rank
      `;
      return NextResponse.json(
        { mode: "avg3", rows },
        { headers: { "Cache-Control": "no-store, max-age=0" } }
      );
    }

    const rows = await sql`
      WITH last_three AS (
        SELECT
          m.athlete_id,
          m.value,
          ROW_NUMBER() OVER (PARTITION BY m.athlete_id ORDER BY m.mark_date DESC NULLS LAST, m.id DESC) AS rn
        FROM marks m
        JOIN athletes a ON a.id = m.athlete_id
        JOIN events e ON e.id = m.event_id
        WHERE e.slug = ${eventSlug}
          AND a.gender = ${genderChar}
          AND a.name != 'Relay Team'
      ),
      avg_marks AS (
        SELECT
          athlete_id,
          AVG(value) AS value
        FROM last_three
        WHERE rn <= 3
        GROUP BY athlete_id
        HAVING COUNT(*) >= 1
      ),
      with_school AS (
        SELECT
          a.name AS athlete_name,
          s.name AS school_name,
          s.id AS school_id,
          e.better_direction,
          am.value
        FROM avg_marks am
        JOIN athletes a ON a.id = am.athlete_id
        JOIN schools s ON s.id = a.school_id
        JOIN events e ON e.slug = ${eventSlug}
      ),
      best_per_athlete AS (
        SELECT athlete_name, school_name, better_direction,
          CASE WHEN better_direction = 'lower' THEN MIN(value) ELSE MAX(value) END AS value
        FROM with_school
        GROUP BY school_id, athlete_name, school_name, better_direction
      )
      SELECT
        ROW_NUMBER() OVER (
          PARTITION BY better_direction
          ORDER BY
            CASE WHEN better_direction = 'lower' THEN value END ASC NULLS LAST,
            CASE WHEN better_direction = 'higher' THEN value END DESC NULLS LAST
        )::int AS rank,
        athlete_name,
        school_name,
        ROUND(value::numeric, 2) AS value
      FROM best_per_athlete
      ORDER BY rank
    `;
    const sanitized = (rows as { rank: number; athlete_name: string; school_name: string; value: number }[]).map(
      (r) => ({ ...r, value: sanitizeDistanceValue(eventSlug, r.value) })
    );
    return NextResponse.json(
      { mode: "avg3", rows: sanitized },
      { headers: { "Cache-Control": "no-store, max-age=0" } }
    );
  } catch (err) {
    console.error("Leaderboard API error:", err);
    return NextResponse.json(
      { error: "Failed to load leaderboard" },
      { status: 500 }
    );
  }
}
