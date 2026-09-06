"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { liveEventSchema, snapshotSchema, type ConnectionState, type LiveEvent, type Snapshot, type StreamName } from "@/lib/contracts";

export function useLiveStream(initial: Snapshot, stream: StreamName, enabled: boolean) {
  const [snapshot, setSnapshot] = useState(initial); const [state, setState] = useState<ConnectionState>(enabled ? "CONNECTING" : "DISABLED");
  const [lastEvent, setLastEvent] = useState<LiveEvent>(); const [retryNonce, setRetryNonce] = useState(0); const attempts = useRef(0); const seen = useRef(new Set<string>());
  const retry = useCallback(() => { attempts.current = 0; setRetryNonce((n) => n + 1); }, []);
  useEffect(() => {
    if (!enabled) { setState("DISABLED"); return; }
    let source: EventSource | undefined; let timer: ReturnType<typeof setTimeout> | undefined; let cancelled = false;
    const poll = async () => { try { const response = await fetch(`/api/live/snapshot/${stream}`, { cache: "no-store" }); if (response.ok) setSnapshot(snapshotSchema.parse(await response.json())); } catch { /* retain the last safe snapshot */ } };
    const connect = () => {
      if (cancelled || document.hidden) return;
      setState(attempts.current ? "DEGRADED" : "CONNECTING"); source = new EventSource(`/api/live/${stream}`);
      source.onopen = () => { attempts.current = 0; setState("LIVE"); };
      const receive = (message: MessageEvent<string>) => { try { const event = liveEventSchema.parse(JSON.parse(message.data)); if (seen.current.has(event.id)) return; seen.current.add(event.id); setLastEvent(event); } catch { setState("DEGRADED"); } };
      source.onmessage = receive;
      ["status.updated", "status.incident", "status.maintenance", "performance.measured", "content.published"].forEach((type) => source?.addEventListener(type, receive as EventListener));
      source.onerror = () => { source?.close(); attempts.current += 1; void poll(); if (!navigator.onLine) setState("OFFLINE"); else if (attempts.current >= 6) setState("ERROR"); else { const delay = Math.min(30_000, 1_000 * 2 ** (attempts.current - 1)) * (0.8 + Math.random() * 0.4); timer = setTimeout(connect, delay); } };
    };
    const visibility = () => { if (document.hidden) { source?.close(); setState("DEGRADED"); } else retry(); };
    const online = () => retry(); const offline = () => { source?.close(); setState("OFFLINE"); };
    document.addEventListener("visibilitychange", visibility); window.addEventListener("online", online); window.addEventListener("offline", offline); connect();
    return () => { cancelled = true; source?.close(); if (timer) clearTimeout(timer); document.removeEventListener("visibilitychange", visibility); window.removeEventListener("online", online); window.removeEventListener("offline", offline); };
  }, [enabled, retryNonce, stream, retry]);
  return { snapshot, state, lastEvent, retry };
}
