import { HUB_BASE_URL } from "@/lib/config";

// Same-origin proxy for GET {HUB_BASE_URL}/stream.
//
// This is a live, infinite MJPEG multipart stream, so:
//  - it must never be cached or statically optimized by Next.js
//  - the upstream body must be piped straight through, never buffered

export const dynamic = "force-dynamic";

export async function GET() {
  let upstream: Response;

  try {
    upstream = await fetch(`${HUB_BASE_URL}/stream`, {
      cache: "no-store",
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        error: "Failed to reach hub camera stream",
        detail: error instanceof Error ? error.message : String(error),
      }),
      {
        status: 502,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({
        error: "Hub camera stream returned an error",
        status: upstream.status,
      }),
      {
        status: 502,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const contentType =
    upstream.headers.get("content-type") ?? "multipart/x-mixed-replace";

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": contentType,
      "cache-control": "no-store, no-cache, must-revalidate",
      connection: "keep-alive",
    },
  });
}
