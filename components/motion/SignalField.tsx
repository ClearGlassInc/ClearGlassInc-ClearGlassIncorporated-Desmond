"use client";

import { useEffect, useRef } from "react";
import { usePerformanceMode } from "./PerformanceModeController";
import { CAPABILITIES, buildEdges } from "./capabilities";

const FPS_CAP = 30;
const DPR_CAP = 2;

/**
 * Draws the constellation's connective tissue: edges plus a slow pulse, with
 * an edge brightening when either endpoint is active. Canvas2D by choice —
 * this is a dozen lines, and a GPU context would cost more than it returns.
 *
 * Budget: frame-capped, DPR-clamped, paused when hidden or offscreen, and the
 * backing store is released on unmount.
 */
export function SignalField({ activeIds }: { activeIds: readonly string[] }): React.JSX.Element | null {
  const { advancedAllowed } = usePerformanceMode();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const activeRef = useRef<readonly string[]>(activeIds);

  // Keep the draw loop reading current state without re-subscribing.
  useEffect(() => {
    activeRef.current = activeIds;
  }, [activeIds]);

  useEffect(() => {
    if (!advancedAllowed) return;
    const canvas = canvasRef.current;
    if (canvas === null) return;
    const ctx = canvas.getContext("2d");
    if (ctx === null) return;

    const byId = new Map(CAPABILITIES.map((c) => [c.id, c]));
    const edges = buildEdges();
    const dpr = Math.min(window.devicePixelRatio, DPR_CAP);
    const minFrame = 1000 / FPS_CAP;
    let raf = 0;
    let last = 0;
    let running = false;

    const resize = (): void => {
      const rect = canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
    };

    const draw = (now: number): void => {
      const { width: w, height: h } = canvas;
      const active = activeRef.current;
      ctx.clearRect(0, 0, w, h);
      ctx.lineCap = "round";
      edges.forEach((edge, i) => {
        const a = byId.get(edge.from);
        const b = byId.get(edge.to);
        if (a === undefined || b === undefined) return;
        const x1 = (a.x / 100) * w;
        const y1 = (a.y / 100) * h;
        const x2 = (b.x / 100) * w;
        const y2 = (b.y / 100) * h;
        const hot = active.includes(edge.from) || active.includes(edge.to);
        ctx.strokeStyle = hot ? "rgba(238,99,122,0.55)" : "rgba(234,70,72,0.16)";
        ctx.lineWidth = (hot ? 1.6 : 0.9) * dpr;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        const t = ((now * (hot ? 0.00022 : 0.00009)) + i * 0.137) % 1;
        ctx.globalAlpha = hot ? 0.85 : 0.32;
        ctx.fillStyle = hot ? "#ee637a" : "#ea4648";
        ctx.beginPath();
        ctx.arc(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, (hot ? 2.4 : 1.5) * dpr, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      });
    };

    const frame = (now: number): void => {
      if (!running) return;
      raf = requestAnimationFrame(frame);
      if (now - last < minFrame) return;
      last = now;
      draw(now);
    };
    const start = (): void => {
      if (running) return;
      running = true;
      last = 0;
      raf = requestAnimationFrame(frame);
    };
    const stop = (): void => {
      running = false;
      if (raf !== 0) cancelAnimationFrame(raf);
      raf = 0;
    };

    const onVisibility = (): void => {
      if (document.hidden) stop();
      else start();
    };

    const io = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry !== undefined && entry.isIntersecting) start();
        else stop();
      },
      { threshold: 0.01 },
    );
    io.observe(canvas);
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    document.addEventListener("visibilitychange", onVisibility);
    resize();

    return () => {
      stop();
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 0;
      canvas.height = 0;
    };
  }, [advancedAllowed]);

  if (!advancedAllowed) return null;
  return <canvas ref={canvasRef} className="cgm-stage__canvas" aria-hidden="true" />;
}
