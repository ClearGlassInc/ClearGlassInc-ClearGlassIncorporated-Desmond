"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMotionMode } from "./use-motion-mode";
import type { MotionMode, MotionPreference } from "./use-motion-mode";

/** Rungs of the visual ladder, richest first. */
export type RenderTier = "webgpu" | "webgl2" | "canvas2d" | "svg" | "css";

export interface PerformanceState {
  mode: MotionMode;
  preference: MotionPreference;
  setPreference: (next: MotionPreference) => void;
  toggle: () => void;
  /** Highest renderer this device actually supports. */
  tier: RenderTier;
  /** True only for hover-capable, fine-pointer devices. */
  finePointer: boolean;
  /** True on small viewports, where expensive compositing is dropped. */
  lowPower: boolean;
  /** Convenience: may we run a continuous GPU/canvas effect at all? */
  advancedAllowed: boolean;
}

const fallback: PerformanceState = {
  mode: "reduced",
  preference: "system",
  setPreference: () => undefined,
  toggle: () => undefined,
  tier: "css",
  finePointer: false,
  lowPower: true,
  advancedAllowed: false,
};

const PerformanceContext = createContext<PerformanceState>(fallback);

/** Probe the renderer ladder once, cheapest reliable checks first. */
function detectTier(): RenderTier {
  if (typeof window === "undefined") return "css";
  const nav = window.navigator as Navigator & { gpu?: unknown };
  if (typeof nav.gpu === "object" && nav.gpu !== null) return "webgpu";
  try {
    const canvas = document.createElement("canvas");
    if (canvas.getContext("webgl2") !== null) return "webgl2";
    if (canvas.getContext("2d") !== null) return "canvas2d";
  } catch {
    return "svg";
  }
  return "svg";
}

export function PerformanceModeController({
  children,
}: {
  children: ReactNode;
}): React.JSX.Element {
  const { mode, preference, setPreference, toggle } = useMotionMode();
  const [tier, setTier] = useState<RenderTier>("css");
  const [finePointer, setFinePointer] = useState(false);
  const [lowPower, setLowPower] = useState(true);

  useEffect(() => {
    setTier(detectTier());
    const pointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    const small = window.matchMedia("(max-width: 900px)");
    const sync = (): void => {
      setFinePointer(pointer.matches);
      setLowPower(small.matches);
    };
    sync();
    pointer.addEventListener("change", sync);
    small.addEventListener("change", sync);
    return () => {
      pointer.removeEventListener("change", sync);
      small.removeEventListener("change", sync);
    };
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-cgm-motion", mode);
  }, [mode]);

  const value = useMemo<PerformanceState>(
    () => ({
      mode,
      preference,
      setPreference,
      toggle,
      tier,
      finePointer,
      lowPower,
      advancedAllowed: mode === "full" && !lowPower && tier !== "css" && tier !== "svg",
    }),
    [mode, preference, setPreference, toggle, tier, finePointer, lowPower],
  );

  return (
    <PerformanceContext.Provider value={value}>{children}</PerformanceContext.Provider>
  );
}

export function usePerformanceMode(): PerformanceState {
  return useContext(PerformanceContext);
}
