// Server-side only config. Do NOT prefix with NEXT_PUBLIC_ since these
// values are only ever read inside route handlers / server components and
// point at an internal service that the browser should never talk to
// directly.
export const HUB_BASE_URL = process.env.HUB_BASE_URL ?? "http://localhost:8000";
