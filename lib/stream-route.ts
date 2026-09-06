import { NextRequest, NextResponse } from "next/server";
import { fabricConfig } from "./config";
import type { StreamName } from "./contracts";
import { authorizeStream, validateOrigin } from "./security";
import { clientKey, principalFromRequest } from "./request";
import { allowRequest } from "./rate-limit";

export function createStreamHandler(stream: StreamName) {
  return async function GET(request: NextRequest): Promise<Response> {
    if (!fabricConfig.enabled || !fabricConfig.enabledStreams.has(stream)) return NextResponse.json({ error: "stream disabled", state: "DISABLED" }, { status: 503 });
    if (!validateOrigin(request)) return NextResponse.json({ error: "origin denied" }, { status: 403 });
    const principal = principalFromRequest(request); const tenant = request.nextUrl.searchParams.get("tenant") ?? undefined;
    if (!authorizeStream(principal, stream, tenant)) return NextResponse.json({ error: "not authorized" }, { status: 403 });
    const limit = principal.role === "anonymous" ? fabricConfig.publicConnectionsPerIp : fabricConfig.authConnectionsPerUser;
    if (!allowRequest(`sse:${principal.subject}:${clientKey(request)}:${stream}`, limit)) return NextResponse.json({ error: "connection limit exceeded" }, { status: 429, headers: { "Retry-After": "60" } });

    const encoder = new TextEncoder(); let heartbeat: ReturnType<typeof setInterval>; let close: ReturnType<typeof setTimeout>;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(`: connected stream=${stream} last-event-id=${request.headers.get("last-event-id")?.slice(0, 128) ?? "none"}\n\n`));
        heartbeat = setInterval(() => controller.enqueue(encoder.encode(`: heartbeat ${Date.now()}\n\n`)), fabricConfig.heartbeatMs);
        close = setTimeout(() => { clearInterval(heartbeat); controller.close(); }, fabricConfig.streamTtlMs);
        request.signal.addEventListener("abort", () => { clearInterval(heartbeat); clearTimeout(close); try { controller.close(); } catch { /* already closed */ } }, { once: true });
      }, cancel() { clearInterval(heartbeat); clearTimeout(close); }
    });
    return new Response(body, { headers: { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache, no-store, must-revalidate", "Connection": "keep-alive", "X-Accel-Buffering": "no", "X-Content-Type-Options": "nosniff" } });
  };
}
