const base = process.env.LEADERBOARD_BASE_URL ?? "http://localhost:3000";
const event = process.env.LEADERBOARD_EVENT ?? "400m";
const gender = process.env.LEADERBOARD_GENDER ?? "men";
const mode = process.env.LEADERBOARD_MODE ?? "pr";
const allGrades = "7,8,9,10,11,12";

function apiUrl(withGrades) {
  const params = new URLSearchParams({
    event,
    gender,
    mode,
  });
  if (withGrades) params.set("grades", allGrades);
  return `${base}/api/leaderboard?${params.toString()}`;
}

function stableStringifyRows(rows) {
  return JSON.stringify(rows ?? []);
}

async function fetchRows(withGrades) {
  const url = apiUrl(withGrades);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${url}`);
  }
  const payload = await response.json();
  return payload.rows ?? [];
}

async function main() {
  const [noFilterRows, explicitAllRows] = await Promise.all([
    fetchRows(false),
    fetchRows(true),
  ]);

  if (stableStringifyRows(noFilterRows) !== stableStringifyRows(explicitAllRows)) {
    console.error("Parity check failed: no-filter rows differ from explicit-all rows");
    console.error(`Base URL: ${base}`);
    console.error(`No-filter rows: ${noFilterRows.length}`);
    console.error(`Explicit-all rows: ${explicitAllRows.length}`);
    process.exit(1);
  }

  console.log("Parity check passed");
  console.log(`Base URL: ${base}`);
  console.log(`Rows compared: ${noFilterRows.length}`);
}

main().catch((err) => {
  console.error("Parity check errored:", err instanceof Error ? err.message : err);
  process.exit(1);
});
