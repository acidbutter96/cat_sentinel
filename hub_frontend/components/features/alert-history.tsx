"use client";

import { useEffect, useState } from "react";
import type { Alert } from "@/lib/types";

const POLL_INTERVAL_MS = 5000;

type FetchState = "loading" | "ok" | "error";

function kindLabel(kind: Alert["kind"]): string {
  return kind === "danger_zone" ? "Danger zone" : "Camera entry";
}

function statusStyle(status: Alert["status"]): string {
  switch (status) {
    case "sent":
      return "bg-emerald-500/10 text-emerald-300 border-emerald-500/40";
    case "failed":
      return "bg-red-500/10 text-red-300 border-red-500/40";
    default:
      return "bg-yellow-500/10 text-yellow-300 border-yellow-500/40";
  }
}

export function AlertHistory() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [state, setState] = useState<FetchState>("loading");

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/alerts", { cache: "no-store" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setAlerts(Array.isArray(data) ? data : []);
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
    return <p className="text-sm text-zinc-500">Loading alerts…</p>;
  }

  if (state === "error") {
    return <p className="text-sm text-red-400">Couldn&apos;t reach the alerts service.</p>;
  }

  if (alerts.length === 0) {
    return <p className="text-sm text-zinc-500">No alerts fired yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {alerts.map((alert) => (
        <li
          key={alert.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950 px-4 py-3"
        >
          <div className="flex items-center gap-3">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                alert.kind === "danger_zone" ? "bg-red-500" : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
            <div>
              <p className="text-sm font-medium text-zinc-100">{kindLabel(alert.kind)}</p>
              <p className="font-mono text-xs text-zinc-500">
                cat {alert.cat_id.slice(0, 8)}
                {alert.zone_id ? ` · zone ${alert.zone_id.slice(0, 8)}` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${statusStyle(alert.status)}`}
            >
              {alert.status}
            </span>
            <span className="text-xs text-zinc-500">
              {new Date(alert.created_at).toLocaleString()}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default AlertHistory;
