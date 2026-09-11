"use client";

import { useCallback, useRef } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

const MAGNET_MAX_PX = 5;

export interface MagneticButtonProps {
  children: ReactNode;
  href: string;
  className?: string;
  withArrow?: boolean;
}

/**
 * A link CTA that leans toward the cursor. Displacement is hard-clamped to
 * 5px: a target that outruns the pointer is worse than one that never moves.
 * Disabled entirely for touch and reduced motion.
 */
export function MagneticButton({
  children,
  href,
  className,
  withArrow = false,
}: MagneticButtonProps): React.JSX.Element {
  const { mode, finePointer } = usePerformanceMode();
  const ref = useRef<HTMLAnchorElement | null>(null);
  const frame = useRef<number | null>(null);
  const enabled = finePointer && mode === "full";

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<HTMLAnchorElement>) => {
      if (!enabled) return;
      const node = ref.current;
      if (node === null) return;
      const rect = node.getBoundingClientRect();
      const dx = (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
      const dy = (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
      const clamp = (n: number): number => Math.max(-1, Math.min(1, n)) * MAGNET_MAX_PX;
      if (frame.current !== null) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        node.style.setProperty("--cgm-btn-x", `${clamp(dx).toFixed(1)}px`);
        node.style.setProperty("--cgm-btn-y", `${clamp(dy).toFixed(1)}px`);
      });
    },
    [enabled],
  );

  const reset = useCallback(() => {
    const node = ref.current;
    if (node === null) return;
    node.style.setProperty("--cgm-btn-x", "0px");
    node.style.setProperty("--cgm-btn-y", "0px");
  }, []);

  return (
    <a
      ref={ref}
      href={href}
      data-no-future-glass
      className={["cgm-btn", className ?? ""].filter(Boolean).join(" ")}
      onPointerMove={onPointerMove}
      onPointerLeave={reset}
      onBlur={reset}
    >
      <span>{children}</span>
      {withArrow ? (
        <span className="cgm-btn__arrow" aria-hidden="true">
          &rarr;
        </span>
      ) : null}
    </a>
  );
}
