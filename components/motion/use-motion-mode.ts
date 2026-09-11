"use client";

import { useCallback, useEffect, useState } from "react";

/** Motion modes a viewer can be in. `system` defers to the OS setting. */
export type MotionPreference = "system" | "full" | "reduced";
export type MotionMode = "full" | "reduced";

const STORAGE_KEY = "cgm-motion-preference";

function isPreference(value: string | null): value is MotionPreference {
  return value === "system" || value === "full" || value === "reduced";
}

function readStored(): MotionPreference {
  if (typeof window === "undefined") return "system";
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return isPreference(raw) ? raw : "system";
  } catch {
    return "system"; // private mode / storage disabled
  }
}

/**
 * Resolves the effective motion mode from the viewer's explicit preference and
 * the OS `prefers-reduced-motion` setting, and keeps it in sync when either
 * changes. Starts as `reduced` on the server and on the first client render so
 * hydration never animates before the real preference is known.
 */
export function useMotionMode(): {
  mode: MotionMode;
  preference: MotionPreference;
  setPreference: (next: MotionPreference) => void;
  toggle: () => void;
} {
  const [preference, setPreferenceState] = useState<MotionPreference>("system");
  const [systemReduced, setSystemReduced] = useState(true);

  useEffect(() => {
    setPreferenceState(readStored());
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setSystemReduced(query.matches);
    const onChange = (event: MediaQueryListEvent): void => {
      setSystemReduced(event.matches);
    };
    query.addEventListener("change", onChange);
    return () => {
      query.removeEventListener("change", onChange);
    };
  }, []);

  const setPreference = useCallback((next: MotionPreference): void => {
    setPreferenceState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* preference is best-effort; the session still honours it */
    }
  }, []);

  const mode: MotionMode =
    preference === "reduced" || (preference === "system" && systemReduced)
      ? "reduced"
      : "full";

  const toggle = useCallback((): void => {
    setPreference(mode === "reduced" ? "full" : "reduced");
  }, [mode, setPreference]);

  return { mode, preference, setPreference, toggle };
}
