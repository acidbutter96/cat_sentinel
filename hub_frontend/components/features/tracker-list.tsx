"use client";

import { useEffect, useState } from "react";
import {
  formatBox,
  isInDangerZone,
  normalizeTrackers,
  trackerLabel,
  type Tracker,
} from "@/lib/types";

const POLL_INTERVAL_MS = 2000;

function snapshotUrl(path: string): string {
  return `/api/snapshots?path=${encodeURIComponent(path)}`;
}

type FetchState = "loading" | "ok" | "error";

export function TrackerList() {
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [state, setState] = useState<FetchState>("loading");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/trackers", { cache: "no-store" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setTrackers(normalizeTrackers(data));
        setState("ok");
        setLastUpdated(new Date());
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

  const anyDanger = trackers.some((t) => isInDangerZone(t) === true);

  return (
    <div className="flex h-full flex-col gap-3 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Tracked cats
        </h2>
        <span
          className={`h-2 w-2 rounded-full ${
            state === "ok"
              ? "bg-emerald-500"
              : state === "error"
                ? "bg-red-500"
                : "bg-yellow-500"
          }`}
          title={state}
        />
      </div>

      {state === "error" && (
        <p className="text-sm text-red-400">
          Couldn&apos;t reach the tracker service.
        </p>
      )}

      {state !== "error" && trackers.length === 0 && (
        <p className="text-sm text-zinc-500">
          {state === "loading" ? "Loading trackers…" : "No cats currently tracked."}
        </p>
      )}

      {anyDanger && (
        <div className="rounded-md border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-300">
          Danger zone alert: a tracked cat is in a danger zone.
        </div>
      )}

      <ul className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {trackers.map((tracker, idx) => {
          const danger = isInDangerZone(tracker);
          const box = formatBox(tracker);
          return (
            <li
              key={tracker.id ?? idx}
              className={`rounded-md border px-3 py-2 text-sm ${
                danger
                  ? "border-red-500/60 bg-red-500/10"
                  : "border-zinc-800 bg-zinc-900"
              }`}
            >
              <div className="flex gap-3">
                {tracker.snapshot_path && (
                  // eslint-disable-next-line @next/next/no-img-element -- snapshot is a runtime API image
                  <img
                    src={snapshotUrl(tracker.snapshot_path)}
                    alt={`${trackerLabel(tracker)} snapshot`}
                    className="h-16 w-20 rounded object-cover"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium text-zinc-100">
                      {trackerLabel(tracker)}
                    </span>
                    {danger !== undefined && (
                      <span
                        className={`shrink-0 text-xs font-semibold uppercase tracking-wide ${
                          danger ? "text-red-400" : "text-emerald-400"
                        }`}
                      >
                        {danger ? "danger zone" : "safe"}
                      </span>
                    )}
                  </div>
                  {typeof tracker.age_seconds === "number" && (
                    <div className="mt-1 text-xs text-zinc-500">
                      seen {tracker.age_seconds.toFixed(1)}s ago
                    </div>
                  )}
                  {typeof tracker.entry_track_id === "number" && (
                    <div className="mt-1 text-xs text-zinc-500">
                      entry tracker #{tracker.entry_track_id}
                    </div>
                  )}
                  {typeof tracker.entry_captured_at === "string" && (
                    <div className="text-xs text-zinc-500">
                      entry {new Date(tracker.entry_captured_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
              {box && (
                <div className="mt-1 font-mono text-xs text-zinc-500">{box}</div>
              )}
              {typeof tracker.confidence === "number" && (
                <div className="mt-0.5 text-xs text-zinc-500">
                  confidence: {(tracker.confidence * 100).toFixed(0)}%
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {lastUpdated && (
        <p className="text-xs text-zinc-600">
          Last updated {lastUpdated.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}

export default TrackerList;
