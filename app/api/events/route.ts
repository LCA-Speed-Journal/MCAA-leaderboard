import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const sql = getSql();
  try {
    const rows = await sql`
      SELECT id, name, slug, discipline, better_direction, unit
      FROM events
      ORDER BY discipline, slug
    `;
    return NextResponse.json({ events: rows });
  } catch (err) {
    console.error("Events API error:", err);
    return NextResponse.json(
      { error: "Failed to load events" },
      { status: 500 }
    );
  }
}
