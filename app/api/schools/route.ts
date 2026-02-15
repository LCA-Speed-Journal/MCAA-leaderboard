// app/api/schools/route.ts
import { NextResponse } from "next/server";
import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const sql = getSql();
  try {
    const rows = await sql`
      SELECT id, name, primary_color, secondary_color
      FROM schools
      ORDER BY name
    `;
    return NextResponse.json({ schools: rows });
  } catch (err) {
    console.error("Schools API error:", err);
    return NextResponse.json(
      { error: "Failed to load schools" },
      { status: 500 }
    );
  }
}
