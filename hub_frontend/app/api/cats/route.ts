import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for GET {HUB_BASE_URL}/cats.
export async function GET() {
  return proxyToHub("/cats");
}

export async function POST(request: Request) {
  return proxyToHub("/cats", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
}
