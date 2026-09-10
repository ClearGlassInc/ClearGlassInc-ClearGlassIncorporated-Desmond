"use client";

import { useEffect, useRef } from "react";
import { usePerformanceMode } from "./PerformanceModeController";

const FPS_CAP = 30;
const DPR_CAP = 2;
const PARTICLES = 46;

interface Particle {
  x: number;
  y: number;
  phase: number;
  speed: number;
}

/** Deterministic seeding, so server and client agree and reloads look the same. */
function seed(count: number): Particle[] {
  const out: Particle[] = [];
  for (let i = 0; i < count; i += 1) {
    const a = Math.sin(i * 12.9898) * 43758.5453;
    const b = Math.sin(i * 78.233) * 12345.6789;
    const c = Math.sin(i * 39.425) * 24634.6345;
    out.push({
      x: a - Math.floor(a),
      y: b - Math.floor(b),
      phase: (c - Math.floor(c)) * Math.PI * 2,
      speed: 0.12 + (c - Math.floor(c)) * 0.22,
    });
  }
  return out;
}

/**
 * Layered atmosphere. The gradient, grid and scan layers are CSS and always
 * present; the particle canvas mounts only where it is affordable. Pointer
 * light is bound only for fine pointers.
 */
export function AtmosphericBackground(): React.JSX.Element {
  const { advancedAllowed, finePointer, mode } = usePerformanceMode();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!finePointer || mode === "reduced") return;
    const root = rootRef.current;
    if (root === null) return;
    let raf = 0;
    const onMove = (event: PointerEvent): void => {
      const { clientX, clientY } = event;
      if (raf !== 0) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        root.style.setProperty("--cgm-mx", `${clientX}px`);
        root.style.setProperty("--cgm-my", `${clientY}px`);
      });
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (raf !== 0) cancelAnimationFrame(raf);
    };
  }, [finePointer, mode]);

  useEffect(() => {
    if (!advancedAllowed) return;
    const canvas = canvasRef.current;
    if (canvas === null) return;
    const ctx = canvas.getContext("2d");
    if (ctx === null) return;

    const parts = seed(PARTICLES);
    const dpr = Math.min(window.devicePixelRatio, DPR_CAP);
    const minFrame = 1000 / FPS_CAP;
    let raf = 0;
    let last = 0;
    let running = false;

    const resize = (): void => {
      canvas.width = Math.round(window.innerWidth * dpr);
      canvas.height = Math.round(window.innerHeight * dpr);
    };
    const draw = (now: number): void => {
      const { width: w, height: h } = canvas;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "rgba(234,70,72,0.5)";
      const r = Math.max(1, h * 0.002);
      for (const p of parts) {
        const y = (p.y + now * 0.000004 * (0.4 + p.speed)) % 1;
        ctx.globalAlpha = Math.max(0.05, 0.25 + 0.45 * Math.sin(now * 0.001 + p.phase));
        ctx.beginPath();
        ctx.arc(p.x * w, y * h, r * dpr, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
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

    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    resize();
    start();

    return () => {
      stop();
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 0;
      canvas.height = 0;
    };
  }, [advancedAllowed]);

  return (
    <div ref={rootRef} className="cgm-atmos" aria-hidden="true">
      <div className="cgm-atmos__field cgm-atmos__field--signal" />
      <div className="cgm-atmos__field cgm-atmos__field--wine" />
      <div className="cgm-atmos__grid" />
      <div className="cgm-atmos__scan" />
      {finePointer && mode === "full" ? <div className="cgm-atmos__cursor" /> : null}
      <div className="cgm-atmos__noise" />
      {advancedAllowed ? <canvas ref={canvasRef} className="cgm-atmos__canvas" /> : null}
    </div>
  );
}
