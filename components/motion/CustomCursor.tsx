"use client";

import { useEffect, useRef } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

const INTERACTIVE = 'a,button,[role="button"],input,select,textarea,summary';

/**
 * An additive ring that trails the pointer. The native cursor is never hidden,
 * so click accuracy and text selection are unaffected. Fine pointers only.
 */
export function CustomCursor(): React.JSX.Element | null {
  const { finePointer, mode } = usePerformanceMode();
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!finePointer || mode === "reduced") return;
    const ring = ref.current;
    if (ring === null) return;
    let raf = 0;

    const onMove = (event: PointerEvent): void => {
      const { clientX, clientY } = event;
      if (raf !== 0) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        ring.style.setProperty("--cgm-cx", `${clientX}px`);
        ring.style.setProperty("--cgm-cy", `${clientY}px`);
      });
    };
    const hot = (event: PointerEvent, on: boolean): void => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest(INTERACTIVE) !== null) {
        ring.classList.toggle("cgm-cursor--hot", on);
      }
    };
    const onOver = (event: PointerEvent): void => hot(event, true);
    const onOut = (event: PointerEvent): void => hot(event, false);

    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerover", onOver, { passive: true });
    document.addEventListener("pointerout", onOut, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerover", onOver);
      document.removeEventListener("pointerout", onOut);
      if (raf !== 0) cancelAnimationFrame(raf);
    };
  }, [finePointer, mode]);

  if (!finePointer || mode === "reduced") return null;
  return <div ref={ref} className="cgm-cursor" aria-hidden="true" />;
}
