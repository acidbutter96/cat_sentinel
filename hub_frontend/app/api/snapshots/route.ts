import { HUB_BASE_URL } from "@/lib/config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const path = new URL(request.url).searchParams.get("path");
  if (!path) return new Response("Missing snapshot path", { status: 400 });

  let upstream: Response;
  try {
    upstream = await fetch(
      `${HUB_BASE_URL}/snapshots?path=${encodeURIComponent(path)}`,
      { cache: "no-store" },
    );
  } catch {
    return new Response("Snapshot service unavailable", { status: 502 });
  }

  if (!upstream.ok || !upstream.body) {
    return new Response("Snapshot not found", { status: upstream.status || 404 });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "image/jpeg",
      "cache-control": "public, max-age=60",
    },
  });
}
