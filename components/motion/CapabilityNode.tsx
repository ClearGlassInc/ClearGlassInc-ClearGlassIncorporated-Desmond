"use client";

import type { Capability } from "./capabilities";

export interface CapabilityNodeProps {
  capability: Capability;
  selected: boolean;
  onToggle: (id: string) => void;
  onPreview: (id: string) => void;
  onPreviewEnd: (id: string) => void;
}

/**
 * A real <button>, positioned from fixed data. Being a button means keyboard
 * order matches reading order for free, and selection is announced through
 * aria-pressed rather than colour alone.
 */
export function CapabilityNode({
  capability,
  selected,
  onToggle,
  onPreview,
  onPreviewEnd,
}: CapabilityNodeProps): React.JSX.Element {
  return (
    <button
      type="button"
      data-no-future-glass
      className="cgm-node"
      style={{ left: `${capability.x}%`, top: `${capability.y}%` }}
      aria-pressed={selected}
      onClick={() => onToggle(capability.id)}
      onFocus={() => onPreview(capability.id)}
      onBlur={() => onPreviewEnd(capability.id)}
      onPointerEnter={() => onPreview(capability.id)}
      onPointerLeave={() => onPreviewEnd(capability.id)}
    >
      <span className="cgm-node__dot" aria-hidden="true" />
      {capability.label}
    </button>
  );
}
