import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for PATCH {HUB_BASE_URL}/cats/{id} -- renaming a cat or
// toggling its active status.
export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.text();
  return proxyToHub(`/cats/${id}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body,
  });
}
