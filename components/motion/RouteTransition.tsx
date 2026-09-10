"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { usePerformanceMode } from "./PerformanceModeController";

/**
 * Crossfades page content on navigation while the surrounding shell stays put.
 * Purely additive: it never blocks interaction, never delays the new route,
 * and back/forward keep working because the transition is driven by pathname
 * rather than by intercepting navigation.
 */
export function RouteTransition({ children }: { children: ReactNode }): React.JSX.Element {
  const pathname = usePathname();
  const { mode } = usePerformanceMode();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (mode === "reduced") {
      setShown(true);
      return;
    }
    setShown(false);
    // Next frame, so the browser has a chance to paint the "out" state.
    const raf = requestAnimationFrame(() => setShown(true));
    return () => {
      cancelAnimationFrame(raf);
    };
  }, [pathname, mode]);

  return (
    <div className={["cgm-route", shown ? "cgm-route--in" : ""].filter(Boolean).join(" ")}>
      {children}
    </div>
  );
}
