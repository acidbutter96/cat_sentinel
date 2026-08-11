import { NextResponse } from "next/server";
import { HUB_BASE_URL } from "@/lib/config";

// Same-origin proxy for GET {HUB_BASE_URL}/trackers.
//
// Keeps the browser from ever needing to know the hub's real address/port
// (and sidesteps CORS entirely, since the browser only ever talks to our
// own origin).
export async function GET() {
  let upstream: Response;

  try {
    upstream = await fetch(`${HUB_BASE_URL}/trackers`, {
      // This is a live tracker snapshot; never let Next.js cache it.
      cache: "no-store",
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to reach hub service",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }

  if (!upstream.ok) {
    return NextResponse.json(
      {
        error: "Hub service returned an error",
        status: upstream.status,
      },
      { status: 502 },
    );
  }

  let data: unknown;
  try {
    data = await upstream.json();
  } catch (error) {
    return NextResponse.json(
      {
        error: "Hub service returned invalid JSON",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }

  return NextResponse.json(data);
}
