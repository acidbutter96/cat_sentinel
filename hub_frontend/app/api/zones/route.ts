import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for GET/POST {HUB_BASE_URL}/zones.
export async function GET() {
  return proxyToHub("/zones");
}

export async function POST(request: Request) {
  const body = await request.text();
  return proxyToHub("/zones", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
}
