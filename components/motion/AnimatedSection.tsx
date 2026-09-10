"use client";

import { useEffect, useRef, useState } from "react";
import type { ElementType, ReactNode } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

export interface AnimatedSectionProps {
  children: ReactNode;
  /** Stagger index within its group; capped by the caller. */
  index?: number;
  as?: ElementType;
  className?: string;
  id?: string;
  "aria-labelledby"?: string;
}

/**
 * Reveals its children once, when they approach the viewport. Under reduced
 * motion the content is rendered in its final state immediately — it is never
 * hidden behind a transition that will not run.
 */
export function AnimatedSection({
  children,
  index = 0,
  as: Tag = "section",
  className,
  id,
  ...aria
}: AnimatedSectionProps): React.JSX.Element {
  const { mode } = usePerformanceMode();
  const ref = useRef<HTMLElement | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (mode === "reduced") {
      setShown(true);
      return;
    }
    const node = ref.current;
    if (node === null || typeof IntersectionObserver === "undefined") {
      setShown(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true);
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.12 },
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
    };
  }, [mode]);

  return (
    <Tag
      ref={ref}
      id={id}
      className={["cgm-r", shown ? "cgm-r--in" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      style={{ "--cgm-delay": `${Math.min(index, 6) * 75}ms` } as React.CSSProperties}
      {...aria}
    >
      {children}
    </Tag>
  );
}
