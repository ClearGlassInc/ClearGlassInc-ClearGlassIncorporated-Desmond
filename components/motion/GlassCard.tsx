"use client";

import { useCallback, useRef } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

export interface GlassCardProps {
  children: ReactNode;
  className?: string;
  /** Bounded tilt on fine pointers. Never enabled for touch or reduced motion. */
  tilt?: boolean;
  /** Border-trace entrance, for service-card grids. */
  trace?: boolean;
}

/**
 * Frosted surface with a pointer-aware highlight. All pointer state is written
 * to CSS custom properties inside one rAF callback, so no frame both reads and
 * writes layout.
 */
export function GlassCard({
  children,
  className,
  tilt = false,
  trace = false,
}: GlassCardProps): React.JSX.Element {
  const { mode, finePointer } = usePerformanceMode();
  const ref = useRef<HTMLDivElement | null>(null);
  const frame = useRef<number | null>(null);

  const interactive = finePointer && mode === "full";

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!interactive) return;
      const node = ref.current;
      if (node === null) return;
      const rect = node.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      if (frame.current !== null) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        node.style.setProperty("--cgm-mx", `${(px * 100).toFixed(2)}%`);
        node.style.setProperty("--cgm-my", `${(py * 100).toFixed(2)}%`);
        if (tilt) {
          node.style.setProperty("--cgm-ry", `${((px * 2 - 1) * 2.5).toFixed(2)}deg`);
          node.style.setProperty("--cgm-rx", `${((py * 2 - 1) * -2.5).toFixed(2)}deg`);
        }
      });
    },
    [interactive, tilt],
  );

  const onPointerLeave = useCallback(() => {
    const node = ref.current;
    if (node === null) return;
    node.style.setProperty("--cgm-rx", "0deg");
    node.style.setProperty("--cgm-ry", "0deg");
  }, []);

  return (
    <div
      ref={ref}
      className={["cgm-glass", tilt && interactive ? "cgm-glass--tilt" : "", trace ? "cgm-glass--trace" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      {children}
    </div>
  );
}
