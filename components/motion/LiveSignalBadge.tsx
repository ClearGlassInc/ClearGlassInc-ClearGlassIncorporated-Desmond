"use client";

import { useEffect, useRef, useState } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

export type SignalState = "healthy" | "warning" | "error" | "stale" | "unavailable";

const LABEL: Record<SignalState, string> = {
  healthy: "Healthy",
  warning: "Warning",
  error: "Error",
  stale: "Stale",
  unavailable: "Unavailable",
};

export interface LiveSignalBadgeProps {
  state: SignalState;
  /** Shown alongside the state; for `stale`, pass the observation time. */
  detail?: string;
}

/**
 * Reflects a real state value. It pulses only when `state` actually changes —
 * there is no timer animating it to look live, because a number that moves
 * without new data is a lie about the system.
 */
export function LiveSignalBadge({ state, detail }: LiveSignalBadgeProps): React.JSX.Element {
  const { mode } = usePerformanceMode();
  const previous = useRef<SignalState | null>(null);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const changed = previous.current !== null && previous.current !== state;
    previous.current = state;
    if (!changed || mode === "reduced") return;
    setPulse(true);
    const timer = window.setTimeout(() => setPulse(false), 600);
    return () => {
      window.clearTimeout(timer);
    };
  }, [state, mode]);

  return (
    <span
      className={["cgm-badge", pulse ? "cgm-badge--pulse" : ""].filter(Boolean).join(" ")}
      data-state={state}
      role="status"
    >
      <span className="cgm-badge__dot" aria-hidden="true" />
      <span>{LABEL[state]}</span>
      {detail !== undefined ? <span className="cgm-badge__detail">{detail}</span> : null}
    </span>
  );
}
