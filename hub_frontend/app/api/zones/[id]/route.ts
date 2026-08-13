import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for PATCH/DELETE {HUB_BASE_URL}/zones/{id}.
export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.text();
  return proxyToHub(`/zones/${id}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body,
  });
}

export async function DELETE(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyToHub(`/zones/${id}`, { method: "DELETE" });
}
