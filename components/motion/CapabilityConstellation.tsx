"use client";

import { useCallback, useMemo, useState } from "react";
import { CAPABILITIES, HUB_ID } from "./capabilities";
import { CapabilityNode } from "./CapabilityNode";
import { GrowthSystemMap } from "./GrowthSystemMap";
import { SignalField } from "./SignalField";

const MAX_PATH = 5;

/**
 * The interactive graph. Selecting two or more capabilities builds a named
 * pathway; the written explanation lives in the DOM beside the graph, so the
 * meaning never depends on the canvas rendering at all.
 */
export function CapabilityConstellation(): React.JSX.Element {
  const [selected, setSelected] = useState<readonly string[]>([]);
  const [focused, setFocused] = useState<string | null>(null);

  const toggle = useCallback((id: string) => {
    setSelected((current) => {
      const next = current.includes(id)
        ? current.filter((entry) => entry !== id)
        : [...current, id];
      return next.length > MAX_PATH ? next.slice(next.length - MAX_PATH) : next;
    });
  }, []);

  const preview = useCallback((id: string) => setFocused(id), []);
  const previewEnd = useCallback(
    (id: string) => setFocused((current) => (current === id ? null : current)),
    [],
  );

  const active = useMemo<readonly string[]>(
    () => (focused === null ? selected : [...selected, focused]),
    [selected, focused],
  );

  const readout =
    CAPABILITIES.find((c) => c.id === (focused ?? HUB_ID)) ?? CAPABILITIES[0];

  const pathway = useMemo<string | null>(() => {
    if (selected.length < 2) return null;
    const labels = selected.map(
      (id) => CAPABILITIES.find((c) => c.id === id)?.label ?? id,
    );
    return `System pathway: ${labels.join(" → ")} — a ${labels.length}-stage engagement. Start with a scoped review of the first stage.`;
  }, [selected]);

  return (
    <div className="cgm-constellation">
      <div className="cgm-stage" data-no-future-glass>
        {/* Static graph underneath; the canvas layers on top when allowed. */}
        <GrowthSystemMap />
        <SignalField activeIds={active} />
        {CAPABILITIES.map((capability) => (
          <CapabilityNode
            key={capability.id}
            capability={capability}
            selected={selected.includes(capability.id)}
            onToggle={toggle}
            onPreview={preview}
            onPreviewEnd={previewEnd}
          />
        ))}
      </div>
      <div className="cgm-readout">
        <h3>{readout?.label}</h3>
        <p>{readout?.copy}</p>
        {/* aria-live so keyboard users hear the pathway they just built. */}
        <p className="cgm-readout__path" aria-live="polite">
          {pathway ?? ""}
        </p>
        <p className="cgm-illustrative">
          Interactive demonstration — illustrative data only.
        </p>
      </div>
    </div>
  );
}
