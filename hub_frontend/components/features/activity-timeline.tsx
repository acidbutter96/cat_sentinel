"use client";

import { useEffect, useState } from "react";
import type { Activity } from "@/lib/types";

const POLL_INTERVAL_MS = 5000;

type FetchState = "loading" | "ok" | "error";

function kindBadge(kind: Activity["kind"]): { label: string; className: string } {
  switch (kind) {
    case "entered_frame":
      return { label: "Entered frame", className: "bg-amber-500/10 text-amber-300 border-amber-500/40" };
    case "alert":
      return { label: "Alert", className: "bg-red-500/10 text-red-300 border-red-500/40" };
    default:
      return { label: "Detection", className: "bg-zinc-800 text-zinc-300 border-zinc-700" };
  }
}

export function ActivityTimeline() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [state, setState] = useState<FetchState>("loading");

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/activities", { cache: "no-store" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setActivities(Array.isArray(data) ? data : []);
        setState("ok");
      } catch {
        if (cancelled) return;
        setState("error");
      }
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (state === "loading") {
    return <p className="text-sm text-zinc-500">Loading activity…</p>;
  }

  if (state === "error") {
    return <p className="text-sm text-red-400">Couldn&apos;t reach the activity service.</p>;
  }

  if (activities.length === 0) {
    return <p className="text-sm text-zinc-500">No activity recorded yet.</p>;
  }

  return (
    <ol className="flex flex-col gap-2 border-l border-zinc-800 pl-4">
      {activities.map((activity) => {
        const badge = kindBadge(activity.kind);
        return (
          <li key={activity.id} className="relative py-1.5">
            <span className="absolute -left-[21px] top-3 h-2 w-2 rounded-full bg-zinc-700" />
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${badge.className}`}
              >
                {badge.label}
              </span>
              <span className="text-xs text-zinc-500">
                {new Date(activity.created_at).toLocaleString()}
              </span>
            </div>
            <p className="mt-1 text-sm text-zinc-200">{activity.message}</p>
          </li>
        );
      })}
    </ol>
  );
}

export default ActivityTimeline;
