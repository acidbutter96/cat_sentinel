import { HUB_BASE_URL } from "@/lib/config";

export const dynamic = "force-dynamic";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let upstream: Response;
  try {
    upstream = await fetch(`${HUB_BASE_URL}/cats/${id}/images`, {
      method: "POST",
      headers: { "content-type": request.headers.get("content-type") ?? "" },
      body: await request.arrayBuffer(),
      cache: "no-store",
    });
  } catch {
    return new Response("Cat image service unavailable", { status: 502 });
  }
  return new Response(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}
