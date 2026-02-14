import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold">MCAA Conference Leaderboard</h1>
      <p className="mt-2 text-gray-600">
        Conference-level track & field standings and benchmarks.
      </p>
      <Link
        href="/leaderboard"
        className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
      >
        View Leaderboard
      </Link>
    </main>
  );
}
