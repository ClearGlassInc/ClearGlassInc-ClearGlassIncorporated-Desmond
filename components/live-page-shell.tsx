"use client";
import { useEffect, useState, type PropsWithChildren } from "react";
import type { Snapshot, StreamName } from "@/lib/contracts";
import { useLiveStream } from "./use-live-stream";
import { LiveConnectionIndicator, LiveDataConsentControl, LiveErrorBoundary, LiveEventStream, LiveReconnectButton, LiveSignalGrid, LiveStatusBanner, LiveSystemMap, StaleDataNotice } from "./live-components";

export function LivePageShell({ initialSnapshot, stream, serverEnabled, children }: PropsWithChildren<{ initialSnapshot: Snapshot; stream: StreamName; serverEnabled: boolean }>) {
  const [consent, setConsent] = useState(false); const [reduced, setReduced] = useState(true);
  useEffect(() => { const query = matchMedia("(prefers-reduced-motion: reduce)"); const sync = () => setReduced(query.matches); sync(); query.addEventListener("change", sync); setConsent(localStorage.getItem("cg-live-consent") === "yes"); return () => query.removeEventListener("change", sync); }, []);
  const enabled = serverEnabled && consent; const { snapshot, state, lastEvent, retry } = useLiveStream(initialSnapshot, stream, enabled);
  const changeConsent = (next: boolean) => { setConsent(next); localStorage.setItem("cg-live-consent", next ? "yes" : "no"); };
  return <LiveErrorBoundary><div className="live-shell" data-reduced-motion={reduced}><header className="live-header"><div><span className="eyebrow">Verified signal surface</span><h1>ClearGlass Live Signal Fabric</h1></div><LiveConnectionIndicator state={state} /></header><LiveStatusBanner state={state} /><StaleDataNotice state={state} /><main>{children}<section className="panel" aria-labelledby="signals-title"><div className="panel-heading"><div><span className="eyebrow">Initial snapshot + validated events</span><h2 id="signals-title">Public system signals</h2></div><LiveReconnectButton onRetry={retry} disabled={!enabled} /></div><LiveSignalGrid signals={snapshot.signals} state={state} /><LiveSystemMap signals={snapshot.signals} state={state} /><LiveEventStream event={lastEvent} /></section></main><footer><LiveDataConsentControl enabled={consent} onChange={changeConsent} /><p>No personal data, fingerprinting, or unverified metrics. Static content remains available when streams fail.</p></footer></div></LiveErrorBoundary>;
}
