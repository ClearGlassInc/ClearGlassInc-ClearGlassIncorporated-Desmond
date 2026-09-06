import { NextRequest } from "next/server";
import type { Principal } from "./security";

/** Replace with the deployment identity proxy. Untrusted client headers never grant a role. */
export function principalFromRequest(_request: NextRequest): Principal {
  return { subject: "anonymous", role: "anonymous" };
}
export function clientKey(request: NextRequest): string {
  return request.headers.get("x-cloud-trace-context")?.slice(0, 64) ?? request.headers.get("x-forwarded-for")?.split(",")[0]?.trim().slice(0, 64) ?? "unknown";
}
