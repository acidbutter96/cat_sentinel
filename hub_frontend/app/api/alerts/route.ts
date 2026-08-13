import { proxyToHub } from "@/lib/proxy";

// Same-origin proxy for GET {HUB_BASE_URL}/alerts.
export async function GET() {
  return proxyToHub("/alerts");
}
