import { HUB_BASE_URL } from "@/lib/config";

export const dynamic = "force-dynamic";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let upstream: Response;
  try {
    upstream = await fetch(`${HUB_BASE_URL}/cats/${id}/photo`, { cache: "no-store" });
  } catch {
    return new Response("Cat image service unavailable", { status: 502 });
  }
  if (!upstream.ok || !upstream.body) return new Response("Cat image not found", { status: 404 });
  return new Response(upstream.body, {
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "image/jpeg",
      "cache-control": "public, max-age=60",
    },
  });
}
