import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for GET {HUB_BASE_URL}/activities.
export async function GET() {
  return proxyToHub("/activities");
}
