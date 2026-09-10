import { CAPABILITIES, HUB_ID, buildEdges } from "./capabilities";

/**
 * Static SVG of the same graph. Server-rendered, no client JS, and used both
 * as the reduced-motion substitute and as the layer beneath the live canvas —
 * so the relationships are in the DOM even when nothing animates.
 */
export function GrowthSystemMap({ title }: { title?: string }): React.JSX.Element {
  const edges = buildEdges();
  const label = title ?? "ClearGlass capability graph";
  return (
    <svg
      className="cgm-stage__svg"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      {edges.map((edge) => {
        const a = CAPABILITIES.find((c) => c.id === edge.from);
        const b = CAPABILITIES.find((c) => c.id === edge.to);
        if (a === undefined || b === undefined) return null;
        return (
          <line
            key={`${edge.from}-${edge.to}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke={edge.to === HUB_ID ? "rgba(234,70,72,0.26)" : "rgba(234,70,72,0.14)"}
            strokeWidth={0.25}
          />
        );
      })}
    </svg>
  );
}
