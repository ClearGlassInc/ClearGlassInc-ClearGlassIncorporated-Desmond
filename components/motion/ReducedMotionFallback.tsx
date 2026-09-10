"use client";

import type { ReactNode } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

export interface ReducedMotionFallbackProps {
  /** Rendered when motion is permitted. */
  children: ReactNode;
  /** Rendered instead when motion is reduced — a diagram, not a blank space. */
  fallback: ReactNode;
}

/**
 * Swaps an animated subtree for a static equivalent. Both branches are real
 * content: reduced motion must never mean less information.
 */
export function ReducedMotionFallback({
  children,
  fallback,
}: ReducedMotionFallbackProps): React.JSX.Element {
  const { mode } = usePerformanceMode();
  return <>{mode === "reduced" ? fallback : children}</>;
}
