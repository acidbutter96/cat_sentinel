import { NextResponse } from "next/server";
import { HUB_BASE_URL } from "@/lib/config";

// Shared body for every /api/* route handler that's a same-origin proxy to
// the hub service (which itself proxies to cat-sentinel -- see
// hub_frontend/app/api/trackers/route.ts and hub/app/proxy/service.py for
// why this indirection exists: the browser should never need to know an
// internal service's real address).
export async function proxyToHub(path: string, init?: RequestInit): Promise<NextResponse> {
  let upstream: Response;

  try {
    upstream = await fetch(`${HUB_BASE_URL}${path}`, { ...init, cache: "no-store" });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to reach hub service",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }

  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const text = await upstream.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: "Hub service returned invalid JSON", detail: text },
        { status: 502 },
      );
    }
  }

  if (!upstream.ok) {
    return NextResponse.json(
      { error: "Hub service returned an error", status: upstream.status, detail: data },
      { status: upstream.status },
    );
  }

  return NextResponse.json(data, { status: upstream.status });
}
