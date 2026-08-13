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
  id?: string | number;
  cat_id?: string;
  cat_name?: string | null;
  bounding_box?: TrackerBox;
  captured_at?: string;
  age_seconds?: number;
  snapshot_path?: string | null;
  entry_frame_path?: string | null;
  entry_track_id?: number | null;
  entry_bounding_box?: TrackerBox | null;
  entry_captured_at?: string | null;
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
  return String(
    tracker.cat_name ?? tracker.label ?? tracker.name ?? tracker.cat_id ?? tracker.id ?? "unknown cat",
  );
}

// --- Cats -------------------------------------------------------------

export type CatSex = "female" | "male" | "unknown";

export interface Cat {
  id: string;
  detected_cat_id: string | null;
  name: string;
  birth_date: string | null;
  sex: CatSex;
  description: string | null;
  photo_path: string | null;
  created_at: string;
  updated_at: string;
}

// --- Danger zones -------------------------------------------------------

export interface ZonePoint {
  x: number;
  y: number;
}

export interface Zone {
  id: string;
  camera_id: string;
  name: string;
  points: ZonePoint[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Alerts -------------------------------------------------------------

export type AlertKind = "danger_zone" | "camera_entry";
export type AlertDeliveryStatus = "pending" | "sent" | "failed";

export interface Alert {
  id: string;
  cat_id: string;
  zone_id: string | null;
  camera_id: string;
  kind: AlertKind;
  status: AlertDeliveryStatus;
  error_message: string | null;
  created_at: string;
}

// --- Activity timeline ----------------------------------------------------

export type ActivityKind = "detection" | "alert" | "entered_frame";

export interface Activity {
  id: string;
  camera_id: string;
  cat_id: string | null;
  kind: ActivityKind;
  message: string;
  created_at: string;
}

export function formatBox(tracker: Tracker): string | null {
  const box = tracker.bounding_box ?? tracker.bbox ?? tracker.box;
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
