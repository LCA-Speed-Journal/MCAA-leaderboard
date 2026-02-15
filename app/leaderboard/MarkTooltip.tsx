"use client";

import { useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type PRProvenance = { mark_date?: string; meet_name?: string | null };
type Avg3Provenance = { mark_date_min?: string; mark_date_max?: string };

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return "—";
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(d);
  } catch {
    return "—";
  }
}

type Props = {
  mode: "pr" | "avg3";
  provenance: PRProvenance | Avg3Provenance;
  children: React.ReactNode;
};

export function MarkTooltip({ mode, provenance, children }: Props) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(
    null
  );
  const triggerRef = useRef<HTMLSpanElement>(null);
  const id = useId();
  const descId = `mark-tooltip-${id.replace(/:/g, "")}`;

  const prProv = mode === "pr" ? (provenance as PRProvenance) : null;
  const avg3Prov = mode === "avg3" ? (provenance as Avg3Provenance) : null;

  let label: string;
  if (mode === "pr") {
    const hasDate = Boolean(prProv?.mark_date);
    const dateStr = hasDate ? formatDate(prProv?.mark_date) : null;
    const meetName = prProv?.meet_name?.trim() || null;
    if (dateStr && meetName) {
      label = `PR set on ${dateStr}. ${meetName}`;
    } else if (dateStr) {
      label = `PR set on ${dateStr}`;
    } else if (meetName) {
      label = `PR at ${meetName}`;
    } else {
      label = "PR (date not in source — load per-meet results for dates)";
    }
  } else {
    const min = avg3Prov?.mark_date_min ? formatDate(avg3Prov.mark_date_min) : "—";
    const max = avg3Prov?.mark_date_max ? formatDate(avg3Prov.mark_date_max) : "—";
    label = `Avg of last 3: ${min} – ${max}`;
  }

  useLayoutEffect(() => {
    if (!visible || !triggerRef.current) {
      setCoords(null);
      return;
    }
    const rect = triggerRef.current.getBoundingClientRect();
    const gap = 6;
    setCoords({
      top: rect.top - gap,
      left: rect.left + rect.width / 2,
    });
  }, [visible]);

  const tooltipEl =
    visible && coords ? (
      <span
        id={descId}
        role="tooltip"
        className="fixed z-[100] -translate-x-1/2 -translate-y-full whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white shadow-lg"
        style={{
          top: coords.top,
          left: coords.left,
          pointerEvents: "none",
        }}
      >
        {label}
      </span>
    ) : null;

  return (
    <>
      <span
        ref={triggerRef}
        tabIndex={0}
        aria-describedby={visible ? descId : undefined}
        className="cursor-default outline-none"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
      >
        {children}
      </span>
      {typeof document !== "undefined" && tooltipEl
        ? createPortal(tooltipEl, document.body)
        : null}
    </>
  );
}
