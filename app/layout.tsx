import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MCAA Conference Leaderboard",
  description: "Conference-level track & field standings and benchmarks",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
