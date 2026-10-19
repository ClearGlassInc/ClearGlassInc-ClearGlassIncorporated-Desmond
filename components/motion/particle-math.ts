/**
 * Convert the canvas backing-store height into a CSS-pixel particle radius.
 * The caller converts the result to backing-store pixels exactly once.
 */
export function particleRadiusCssPixels(backingHeight: number, dpr: number): number {
  const safeDpr = Number.isFinite(dpr) && dpr > 0 ? dpr : 1;
  return Math.max(1, (backingHeight / safeDpr) * 0.002);
}
