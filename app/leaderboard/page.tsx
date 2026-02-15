"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { MarkTooltip } from "./MarkTooltip";

const GRADES = [7, 8, 9, 10, 11, 12] as const;

type EventRow = { id: number; name: string; slug: string; discipline: string; unit: string };
type SchoolRow = {
  id: number;
  name: string;
  primary_color: string | null;
  secondary_color: string | null;
};
type LeaderboardRow = {
  rank: number;
  athlete_name: string;
  school_name: string;
  school_id: number;
  value: number;
  grade: number | null;
  mark_date?: string;
  meet_name?: string | null;
  mark_date_min?: string;
  mark_date_max?: string;
};
type Benchmarks = {
  slug: string;
  section_qual: number | null;
  state_qual: number | null;
  conference_podium_avg: number | null;
};

const EVENT_GROUPS: { label: string; slugs: string[] }[] = [
  { label: "Sprints", slugs: ["100m", "200m", "400m"] },
  { label: "Distance", slugs: ["800m", "1600m", "3200m"] },
  { label: "Hurdles", slugs: ["100h", "110h", "300h", "60h"] },
  { label: "Relays", slugs: ["4x100", "4x200", "4x400", "4x800"] },
  { label: "Jumps", slugs: ["lj", "tj", "hj", "pv"] },
  { label: "Throws", slugs: ["sp", "discus"] },
];

/** Hex to rgba for low-opacity row background. */
function hexToRgba(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 0xff;
  const g = (n >> 8) & 0xff;
  const b = n & 0xff;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Parse grades from URL (e.g. ?grades=9,10) → number[]; only 7–12. */
function gradesFromSearchParams(searchParams: ReturnType<typeof useSearchParams>): number[] {
  const raw = searchParams.get("grades");
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((g) => g >= 7 && g <= 12);
}

export default function LeaderboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const grades = gradesFromSearchParams(searchParams);

  const toggleGrade = (g: number) => {
    const next = grades.includes(g)
      ? grades.filter((x) => x !== g)
      : [...grades, g].sort((a, b) => a - b);
    const params = new URLSearchParams(searchParams.toString());
    if (eventSlug) params.set("event", eventSlug);
    params.set("gender", gender);
    params.set("mode", mode);
    if (next.length) params.set("grades", next.join(","));
    else params.delete("grades");
    const q = params.toString();
    router.replace(q ? `/leaderboard?${q}` : "/leaderboard", { scroll: false });
  };

  const [events, setEvents] = useState<EventRow[]>([]);
  const [eventSlug, setEventSlug] = useState<string>("");
  const [gender, setGender] = useState<"men" | "women">("men");
  const [mode, setMode] = useState<"pr" | "avg3">("pr");
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmarks | null>(null);
  const [schools, setSchools] = useState<SchoolRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/schools")
      .then(async (r) => {
        const text = await r.text();
        if (!r.ok) return;
        const data = text ? (JSON.parse(text) as { schools?: SchoolRow[] }) : {};
        if (data.schools?.length) setSchools(data.schools);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch("/api/events")
      .then(async (r) => {
        const text = await r.text();
        if (!r.ok) {
          const msg = text.startsWith("{") ? (JSON.parse(text) as { error?: string }).error : null;
          throw new Error(msg ?? `Events: ${r.status}`);
        }
        return text ? (JSON.parse(text) as { events?: EventRow[] }) : { events: [] };
      })
      .then((data) => {
        if (data.events?.length) {
          setEvents(data.events);
          const bySlug = Object.fromEntries(data.events.map((e: EventRow) => [e.slug, e]));
          const firstSlug =
            EVENT_GROUPS.flatMap((g) => g.slugs).find((s) => bySlug[s]) ??
            data.events[0].slug;
          setEventSlug((prev) => prev || firstSlug);
        }
      })
      .catch((e) => setError(e.message || "Failed to load events"));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load events once on mount
  }, []);

  useEffect(() => {
    if (!eventSlug) return;
    setLoading(true);
    setError(null);
    const parseJson = async (r: Response, label: string) => {
      const text = await r.text();
      if (!r.ok) {
        let msg: string | null = null;
        if (text.startsWith("{")) {
          try {
            msg = (JSON.parse(text) as { error?: string }).error ?? null;
          } catch {
            /* use status below */
          }
        }
        throw new Error(msg ?? `${label}: ${r.status}`);
      }
      try {
        return text ? (JSON.parse(text) as unknown) : {};
      } catch {
        throw new Error(`${label}: invalid response`);
      }
    };

    const leaderboardUrl =
      `/api/leaderboard?event=${encodeURIComponent(eventSlug)}&gender=${gender}&mode=${mode}` +
      (grades.length > 0 ? `&grades=${grades.join(",")}` : "");

    Promise.all([
      fetch(leaderboardUrl, { cache: "no-store" }).then((r) =>
        parseJson(r, "Leaderboard")
      ),
      fetch(`/api/benchmarks?event=${encodeURIComponent(eventSlug)}`, {
        cache: "no-store",
      }).then((r) => parseJson(r, "Benchmarks")),
    ])
      .then(([lb, b]) => {
        const lbData = lb as {
          error?: string;
          detail?: string;
          rows?: LeaderboardRow[];
        };
        const bData = b as { error?: string } & Benchmarks;
        if (lbData.error)
          throw new Error(lbData.detail ?? lbData.error);
        if (bData.error) throw new Error(bData.error);
        setRows(lbData.rows || []);
        setBenchmarks(bData);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load leaderboard"))
      .finally(() => setLoading(false));
  }, [eventSlug, gender, mode, grades.length, grades.join(",")]);

  const currentEvent = events.find((e) => e.slug === eventSlug);
  const unit = currentEvent?.unit ?? "time";
  const slug = currentEvent?.slug ?? "";

  const eventsBySlug = Object.fromEntries(events.map((e) => [e.slug, e]));
  const groupedEvents = EVENT_GROUPS.map(({ label, slugs }) => ({
    label,
    events: slugs
      .map((s) => eventsBySlug[s])
      .filter((e): e is EventRow => e != null),
  })).filter((g) => g.events.length > 0);

  const FEET_INCHES_SLUGS = ["hj", "lj", "tj", "pv", "sp", "discus"];

  const formatValue = (v: number) => {
    if (unit === "time") return formatTime(v);
    if (FEET_INCHES_SLUGS.includes(slug)) return formatFeetInches(v);
    return `${Number(v).toFixed(2)}m`;
  };

  function formatFeetInches(meters: number): string {
    const totalInches = Number(meters) / 0.0254;
    const feet = Math.floor(totalInches / 12);
    const rem = totalInches % 12;
    const inchesStr = rem % 1 === 0 ? String(Math.round(rem)) : rem.toFixed(1);
    return `${feet}'${inchesStr}"`;
  }

  function formatTime(seconds: number) {
    const n = Number(seconds);
    if (n >= 60) {
      const m = Math.floor(n / 60);
      const s = (n % 60).toFixed(2);
      return `${m}:${s.padStart(5, "0")}`;
    }
    return `${n.toFixed(2)}`;
  }

  const emptyNoGrades = !loading && rows.length === 0 && !error && grades.length > 0;

  return (
    <main className="min-h-screen bg-gray-100 p-4 md:p-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">MCAA Conference Leaderboard</h1>
        <p className="mt-1 text-gray-600">
          Select event and gender. Toggle PR vs average of last 3.
        </p>

        <div className="mt-6 flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Event
            </label>
            <select
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={eventSlug}
              onChange={(e) => setEventSlug(e.target.value)}
            >
              {groupedEvents.map((group) => (
                <optgroup key={group.label} label={group.label}>
                  {group.events.map((e) => (
                    <option key={e.id} value={e.slug}>
                      {e.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Gender
            </label>
            <select
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={gender}
              onChange={(e) => setGender(e.target.value as "men" | "women")}
            >
              <option value="men">Men</option>
              <option value="women">Women</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              View by
            </label>
            <div className="mt-2 flex gap-2">
              <button
                className={`rounded px-3 py-2 text-sm font-medium ${
                  mode === "pr"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
                onClick={() => setMode("pr")}
              >
                PR
              </button>
              <button
                className={`rounded px-3 py-2 text-sm font-medium ${
                  mode === "avg3"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
                onClick={() => setMode("avg3")}
              >
                Avg of last 3
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Grade (optional; leave unselected for all)
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              {GRADES.map((g) => (
                <button
                  key={g}
                  type="button"
                  aria-pressed={grades.includes(g)}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                    grades.includes(g)
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                  onClick={() => toggleGrade(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-lg bg-white p-4 shadow-sm md:p-6">
          {error && (
            <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700" role="alert">
              {error}
            </div>
          )}

          {benchmarks && !error && (
            <div className="mb-4 rounded bg-gray-50 p-3 text-sm text-gray-800">
              <span className="font-medium text-gray-700">Benchmarks: </span>
              <span>
                Section qual:{" "}
                {benchmarks.section_qual != null
                  ? formatValue(benchmarks.section_qual)
                  : "—"}
              </span>
              <span className="ml-4">
                State qual:{" "}
                {benchmarks.state_qual != null
                  ? formatValue(benchmarks.state_qual)
                  : "—"}
              </span>
              <span className="ml-4">
                Conference podium avg:{" "}
                {benchmarks.conference_podium_avg != null
                  ? formatValue(benchmarks.conference_podium_avg)
                  : "—"}
              </span>
            </div>
          )}

          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-gray-500">Loading…</p>
            ) : rows.length === 0 ? (
              <p className="text-gray-600">
                {emptyNoGrades
                  ? "No athletes in selected grades."
                  : "No marks for this event. Load data with the scraper (e.g. sync_school or load_fixture)."}
              </p>
            ) : (
              <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                <thead className="bg-gray-50">
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">
                      Rank
                    </th>
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">
                      Athlete
                    </th>
                    <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">
                      School
                    </th>
                    <th className="px-4 py-2 text-right text-sm font-medium text-gray-600">
                      Mark
                    </th>
                  </tr>
                </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {rows.map((r, i) => {
                  const school = schools.find((s) => s.id === r.school_id);
                  const primaryColor = school?.primary_color ?? null;
                  const accentColor =
                    school?.secondary_color ?? primaryColor ?? "#e5e7eb";
                  const rowBg =
                    primaryColor != null ? hexToRgba(primaryColor, 0.08) : undefined;
                  return (
                    <tr
                      key={`${r.rank}-${r.athlete_name}-${r.school_name}-${r.value}-${i}`}
                      style={{
                        borderLeftWidth: 4,
                        borderLeftColor: accentColor,
                        backgroundColor: rowBg,
                      }}
                    >
                      <td className="px-4 py-2 text-sm text-gray-600">{r.rank}</td>
                      <td className="px-4 py-2 text-sm">
                        <span className="font-semibold text-gray-800">
                          {r.athlete_name}
                        </span>
                        {r.grade != null && (
                          <>
                            {" — "}
                            <span className="font-normal text-gray-500">
                              {r.grade}
                            </span>
                          </>
                        )}
                      </td>
                      <td
                        className="px-4 py-2 text-sm italic text-gray-800"
                        style={{ color: primaryColor ?? undefined }}
                      >
                        {r.school_name}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm font-semibold text-gray-800">
                        <MarkTooltip
                          mode={mode}
                          provenance={
                            mode === "pr"
                              ? {
                                  mark_date: r.mark_date,
                                  meet_name: r.meet_name,
                                }
                              : {
                                  mark_date_min: r.mark_date_min,
                                  mark_date_max: r.mark_date_max,
                                }
                          }
                        >
                          {formatValue(Number(r.value))}
                        </MarkTooltip>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
