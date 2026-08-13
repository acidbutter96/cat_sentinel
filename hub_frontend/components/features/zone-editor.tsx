"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Zone, ZonePoint } from "@/lib/types";

// Single-camera deployment for v1 -- matches cat-sentinel's own default
// (see cat-sentinel/app/settings/config.py: camera_id = "default").
const CAMERA_ID = "default";
const STREAM_URL = "/api/stream";

interface Size {
  width: number;
  height: number;
}

interface Rect extends Size {
  left: number;
  top: number;
}

/** The area the video actually occupies inside its box under
 * object-fit: contain -- needed so click coordinates (and the zone overlay)
 * account for letterboxing instead of assuming the image fills its box.
 */
function computeContainedRect(container: Size, natural: Size): Rect {
  const containerRatio = container.width / container.height;
  const naturalRatio = natural.width / natural.height;
  let width: number;
  let height: number;
  if (naturalRatio > containerRatio) {
    width = container.width;
    height = container.width / naturalRatio;
  } else {
    height = container.height;
    width = container.height * naturalRatio;
  }
  return { left: (container.width - width) / 2, top: (container.height - height) / 2, width, height };
}

function polygonToSvgPoints(points: ZonePoint[]): string {
  return points.map((p) => `${p.x},${p.y}`).join(" ");
}

async function fetchZones(): Promise<Zone[]> {
  const res = await fetch("/api/zones", { cache: "no-store" });
  if (!res.ok) throw new Error(`status ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export function ZoneEditor() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerSize, setContainerSize] = useState<Size | null>(null);
  const [naturalSize, setNaturalSize] = useState<Size | null>(null);
  const [streamError, setStreamError] = useState(false);

  const [zones, setZones] = useState<Zone[]>([]);
  const [zonesState, setZonesState] = useState<"loading" | "ok" | "error">("loading");

  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<ZonePoint[]>([]);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Reusable reload for after a mutation (save/toggle/delete) -- always
  // called from an event handler, never directly from an effect body, so it
  // doesn't hit the "no setState directly in an effect" lint rule below.
  const loadZones = useCallback(async () => {
    try {
      const data = await fetchZones();
      setZones(data);
      setZonesState("ok");
    } catch {
      setZonesState("error");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchZones();
        if (cancelled) return;
        setZones(data);
        setZonesState("ok");
      } catch {
        if (!cancelled) setZonesState("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setContainerSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const containedRect = useMemo(() => {
    if (!containerSize || !naturalSize) return null;
    return computeContainedRect(containerSize, naturalSize);
  }, [containerSize, naturalSize]);

  function handleImageLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const img = e.currentTarget;
    if (img.naturalWidth > 0 && img.naturalHeight > 0) {
      setNaturalSize({ width: img.naturalWidth, height: img.naturalHeight });
    }
    setStreamError(false);
  }

  function handleContainerClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!drawing || !containedRect || !naturalSize || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const relX = e.clientX - rect.left - containedRect.left;
    const relY = e.clientY - rect.top - containedRect.top;
    if (relX < 0 || relY < 0 || relX > containedRect.width || relY > containedRect.height) {
      return; // clicked in the letterboxed margin, not on the frame itself
    }
    const x = Math.round((relX / containedRect.width) * naturalSize.width);
    const y = Math.round((relY / containedRect.height) * naturalSize.height);
    setPoints((prev) => [...prev, { x, y }]);
  }

  function startDrawing() {
    setDrawing(true);
    setPoints([]);
    setFormError(null);
  }

  function cancelDrawing() {
    setDrawing(false);
    setPoints([]);
    setName("");
    setFormError(null);
  }

  function undoLastPoint() {
    setPoints((prev) => prev.slice(0, -1));
  }

  async function saveZone() {
    if (points.length < 3) {
      setFormError("A danger zone needs at least 3 points.");
      return;
    }
    if (!name.trim()) {
      setFormError("Give the zone a name.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const res = await fetch("/api/zones", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ camera_id: CAMERA_ID, name: name.trim(), points }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      await loadZones();
      cancelDrawing();
    } catch {
      setFormError("Couldn't save the zone -- try again.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleZoneActive(zone: Zone) {
    try {
      const res = await fetch(`/api/zones/${zone.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ is_active: !zone.is_active }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      await loadZones();
    } catch {
      setZonesState("error");
    }
  }

  async function deleteZone(zone: Zone) {
    try {
      const res = await fetch(`/api/zones/${zone.id}`, { method: "DELETE" });
      if (!res.ok && res.status !== 204) throw new Error(`status ${res.status}`);
      await loadZones();
    } catch {
      setZonesState("error");
    }
  }

  const overlayStyle = containedRect
    ? {
        left: containedRect.left,
        top: containedRect.top,
        width: containedRect.width,
        height: containedRect.height,
      }
    : { inset: 0 };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <div
          ref={containerRef}
          onClick={handleContainerClick}
          className={`relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border border-zinc-800 bg-black ${
            drawing ? "cursor-crosshair" : ""
          }`}
        >
          {!streamError ? (
            // eslint-disable-next-line @next/next/no-img-element -- MJPEG multipart stream
            <img
              src={STREAM_URL}
              alt="Camera feed for drawing danger zones"
              onLoad={handleImageLoad}
              onError={() => setStreamError(true)}
              className="h-full w-full object-contain"
            />
          ) : (
            <p className="p-8 text-center text-sm text-zinc-400">
              Feed unavailable -- can&apos;t draw zones without a live frame to reference.
            </p>
          )}

          {naturalSize && (
            <svg
              className="pointer-events-none absolute"
              style={overlayStyle}
              viewBox={`0 0 ${naturalSize.width} ${naturalSize.height}`}
              preserveAspectRatio="none"
            >
              {zones
                .filter((z) => z.is_active)
                .map((zone) => (
                  <polygon
                    key={zone.id}
                    points={polygonToSvgPoints(zone.points)}
                    fill="rgba(239, 68, 68, 0.18)"
                    stroke="rgb(239, 68, 68)"
                    strokeWidth={Math.max(naturalSize.width / 400, 1.5)}
                  />
                ))}

              {points.length > 0 && (
                <polygon
                  points={polygonToSvgPoints(points)}
                  fill="rgba(251, 191, 36, 0.2)"
                  stroke="rgb(251, 191, 36)"
                  strokeWidth={Math.max(naturalSize.width / 400, 1.5)}
                  strokeDasharray="6 4"
                />
              )}
              {points.map((p, idx) => (
                <circle
                  key={idx}
                  cx={p.x}
                  cy={p.y}
                  r={Math.max(naturalSize.width / 150, 3)}
                  fill="rgb(251, 191, 36)"
                />
              ))}
            </svg>
          )}
        </div>

        {drawing ? (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Zone name (e.g. Kitchen counter)"
              className="min-w-[200px] flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 outline-none focus:border-amber-500"
            />
            <span className="text-xs text-zinc-400">
              {points.length < 3
                ? `Click the frame to add points (${points.length} so far, need at least 3).`
                : `${points.length} points.`}
            </span>
            <button
              type="button"
              onClick={undoLastPoint}
              disabled={points.length === 0}
              className="rounded-md border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-900 disabled:opacity-40"
            >
              Undo point
            </button>
            <button
              type="button"
              onClick={saveZone}
              disabled={saving || points.length < 3}
              className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save zone"}
            </button>
            <button
              type="button"
              onClick={cancelDrawing}
              className="rounded-md border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-900"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={startDrawing}
            className="self-start rounded-md bg-amber-500 px-4 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-amber-400"
          >
            Draw new danger zone
          </button>
        )}
        {formError && <p className="text-sm text-red-400">{formError}</p>}
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Zones ({zones.length})
        </h2>
        {zonesState === "loading" && <p className="text-sm text-zinc-500">Loading zones…</p>}
        {zonesState === "error" && (
          <p className="text-sm text-red-400">Couldn&apos;t reach the zones service.</p>
        )}
        {zonesState === "ok" && zones.length === 0 && (
          <p className="text-sm text-zinc-500">No danger zones defined yet.</p>
        )}
        <ul className="flex flex-col gap-2">
          {zones.map((zone) => (
            <li
              key={zone.id}
              className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 ${
                zone.is_active ? "border-zinc-800 bg-zinc-950" : "border-zinc-900 bg-zinc-950/50 opacity-60"
              }`}
            >
              <div>
                <p className="text-sm font-medium text-zinc-100">{zone.name}</p>
                <p className="text-xs text-zinc-500">{zone.points.length} points</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => toggleZoneActive(zone)}
                  className="rounded-md border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-900"
                >
                  {zone.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  onClick={() => deleteZone(zone)}
                  className="rounded-md border border-red-500/40 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/10"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default ZoneEditor;
