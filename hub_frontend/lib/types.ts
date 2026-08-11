// Shape of a single tracker entry returned by GET /trackers on the hub
// service. The hub is a separate service under active development, so we
// keep this permissive: known fields are typed, but we tolerate (and
// display) extra fields we don't know about yet.
export interface TrackerBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Tracker {
  id: string | number;
  label?: string;
  name?: string;
  bbox?: TrackerBox | number[];
  box?: TrackerBox | number[];
  confidence?: number;
  in_danger_zone?: boolean;
  danger_zone?: boolean;
  dangerZone?: boolean;
  [key: string]: unknown;
}

export type TrackersResponse = Tracker[] | { trackers: Tracker[] };

export function normalizeTrackers(data: TrackersResponse | null | undefined): Tracker[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.trackers)) return data.trackers;
  return [];
}

export function isInDangerZone(tracker: Tracker): boolean | undefined {
  if (typeof tracker.in_danger_zone === "boolean") return tracker.in_danger_zone;
  if (typeof tracker.danger_zone === "boolean") return tracker.danger_zone;
  if (typeof tracker.dangerZone === "boolean") return tracker.dangerZone;
  return undefined;
}

export function trackerLabel(tracker: Tracker): string {
  return String(tracker.label ?? tracker.name ?? tracker.id ?? "unknown cat");
}

export function formatBox(tracker: Tracker): string | null {
  const box = tracker.bbox ?? tracker.box;
  if (!box) return null;
  if (Array.isArray(box)) {
    return box.map((n) => (typeof n === "number" ? n.toFixed(0) : n)).join(", ");
  }
  const { x, y, width, height } = box;
  if (
    typeof x === "number" &&
    typeof y === "number" &&
    typeof width === "number" &&
    typeof height === "number"
  ) {
    return `x:${x.toFixed(0)} y:${y.toFixed(0)} w:${width.toFixed(0)} h:${height.toFixed(0)}`;
  }
  return null;
}
