import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const REFRESH_SECRET = process.env.REFRESH_SECRET;

export async function POST(request: NextRequest) {
  const auth = request.headers.get("authorization");
  const token = auth?.startsWith("Bearer ") ? auth.slice(7) : null;

  if (!REFRESH_SECRET || token !== REFRESH_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // MVP: Scraper runs externally (cron-job.org or GitHub Actions runs Python script).
  // Optionally enqueue or invoke scraper here when you have a worker.
  return NextResponse.json({
    message:
      "Refresh endpoint OK. Run the Python scraper externally (e.g. cron with DATABASE_URL).",
  });
}
