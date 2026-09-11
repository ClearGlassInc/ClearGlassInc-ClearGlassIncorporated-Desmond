/**
 * The signal core at the centre of the hero. Pure SVG with a CSS-driven
 * shimmer, so it costs nothing on the main thread and renders on the server.
 */
export function GlassPrism({ size = 128 }: { size?: number }): React.JSX.Element {
  return (
    <svg
      className="cgm-prism"
      width={size}
      height={size}
      viewBox="0 0 100 100"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="cgm-prism-face" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ee637a" stopOpacity="0.85" />
          <stop offset="55%" stopColor="#ea4648" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#7a123d" stopOpacity="0.7" />
        </linearGradient>
      </defs>
      <polygon points="50,8 92,74 8,74" fill="url(#cgm-prism-face)" />
      <polygon points="50,8 92,74 8,74" fill="none" stroke="#ee637a" strokeOpacity="0.55" strokeWidth="1.2" />
      <line x1="50" y1="8" x2="50" y2="74" stroke="#f3eeee" strokeOpacity="0.18" strokeWidth="0.8" />
    </svg>
  );
}
