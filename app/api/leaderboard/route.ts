import { NextRequest, NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

type Mode = "pr" | "avg3";
type Gender = "men" | "women";

const genderMap: Record<Gender, string> = { men: "M", women: "F" };

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

  try {
    if (mode === "pr") {
      const rows = await sql`
        WITH best_marks AS (
          SELECT
            a.id AS athlete_id,
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
          GROUP BY a.id, a.name, s.name, e.better_direction
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
      return NextResponse.json({ mode: "pr", rows });
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
          e.better_direction,
          am.value
        FROM avg_marks am
        JOIN athletes a ON a.id = am.athlete_id
        JOIN schools s ON s.id = a.school_id
        JOIN events e ON e.slug = ${eventSlug}
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
      FROM with_school
      ORDER BY rank
    `;
    return NextResponse.json({ mode: "avg3", rows });
  } catch (err) {
    console.error("Leaderboard API error:", err);
    return NextResponse.json(
      { error: "Failed to load leaderboard" },
      { status: 500 }
    );
  }
}
