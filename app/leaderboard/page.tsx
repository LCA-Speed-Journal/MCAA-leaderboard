"use client";

import { useEffect, useState } from "react";

type EventRow = { id: number; name: string; slug: string; discipline: string; unit: string };
type LeaderboardRow = { rank: number; athlete_name: string; school_name: string; value: number };
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

export default function LeaderboardPage() {
  const [events, setEvents] = useState<EventRow[]>([]);
  const [eventSlug, setEventSlug] = useState<string>("");
  const [gender, setGender] = useState<"men" | "women">("men");
  const [mode, setMode] = useState<"pr" | "avg3">("pr");
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmarks | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/events")
      .then((r) => r.json())
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
      .catch(() => setError("Failed to load events"));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load events once on mount
  }, []);

  useEffect(() => {
    if (!eventSlug) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(
        `/api/leaderboard?event=${encodeURIComponent(eventSlug)}&gender=${gender}&mode=${mode}`,
        { cache: "no-store" }
      ).then((r) => r.json()),
      fetch(`/api/benchmarks?event=${encodeURIComponent(eventSlug)}`, {
        cache: "no-store",
      }).then((r) => r.json()),
    ])
      .then(([lb, b]) => {
        if (lb.error) throw new Error(lb.error);
        if (b.error) throw new Error(b.error);
        setRows(lb.rows || []);
        setBenchmarks(b);
      })
      .catch((e) => setError(e.message || "Failed to load leaderboard"))
      .finally(() => setLoading(false));
  }, [eventSlug, gender, mode]);

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

  return (
    <main className="min-h-screen p-4 md:p-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-2xl font-bold">MCAA Conference Leaderboard</h1>
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
        </div>

        {benchmarks && (
          <div className="mt-4 rounded bg-gray-50 p-3 text-sm">
            <span className="font-medium">Benchmarks: </span>
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

        {error && (
          <div className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</div>
        )}

        <div className="mt-6 overflow-x-auto">
          {loading ? (
            <p className="text-gray-500">Loading…</p>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">
                    Rank
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">
                    Athlete
                  </th>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">
                    School
                  </th>
                  <th className="px-4 py-2 text-right text-sm font-semibold text-gray-700">
                    Mark
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {rows.map((r, i) => (
                  <tr key={`${r.rank}-${r.athlete_name}-${r.school_name}-${r.value}-${i}`}>
                    <td className="px-4 py-2 text-sm">{r.rank}</td>
                    <td className="px-4 py-2 text-sm">{r.athlete_name}</td>
                    <td className="px-4 py-2 text-sm">{r.school_name}</td>
                    <td className="px-4 py-2 text-right font-mono text-sm">
                      {formatValue(Number(r.value))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loading && rows.length === 0 && !error && (
            <p className="mt-2 text-gray-500">
              No marks for this event. Load data with the scraper (e.g. sync_school or load_fixture).
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
