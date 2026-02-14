import { NextRequest, NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const eventSlug = request.nextUrl.searchParams.get("event");
  if (!eventSlug) {
    return NextResponse.json(
      { error: "Query param 'event' is required" },
      { status: 400 }
    );
  }
  const sql = getSql();
  try {
    const rows = (await sql`
      SELECT e.slug, b.section_qual, b.state_qual, b.conference_podium_avg
      FROM benchmarks b
      JOIN events e ON e.id = b.event_id
      WHERE e.slug = ${eventSlug}
    `) as { slug: string; section_qual: number | null; state_qual: number | null; conference_podium_avg: number | null }[];
    const b = rows[0];
    if (!b) {
      return NextResponse.json({
        slug: eventSlug,
        section_qual: null,
        state_qual: null,
        conference_podium_avg: null,
      });
    }
    return NextResponse.json({
      slug: b.slug,
      section_qual: b.section_qual != null ? Number(b.section_qual) : null,
      state_qual: b.state_qual != null ? Number(b.state_qual) : null,
      conference_podium_avg:
        b.conference_podium_avg != null ? Number(b.conference_podium_avg) : null,
    });
  } catch (err) {
    console.error("Benchmarks API error:", err);
    return NextResponse.json(
      { error: "Failed to load benchmarks" },
      { status: 500 }
    );
  }
}
