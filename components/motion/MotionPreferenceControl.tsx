"use client";

import { usePerformanceMode } from "./PerformanceModeController";

/**
 * Visible opt-out. Stored locally only — no account write, no network call.
 * Positioned bottom-left because the legacy site anchors two floating widgets
 * bottom-right; keeping the corners disjoint avoids burying either one.
 */
export function MotionPreferenceControl({
  className,
}: {
  className?: string;
}): React.JSX.Element {
  const { mode, toggle } = usePerformanceMode();
  const reduced = mode === "reduced";
  return (
    <button
      type="button"
      data-no-future-glass
      aria-pressed={reduced}
      onClick={toggle}
      className={["cgm-pref", className ?? ""].filter(Boolean).join(" ")}
    >
      {reduced ? "Visual effects: reduced" : "Reduce visual effects"}
    </button>
  );
}
