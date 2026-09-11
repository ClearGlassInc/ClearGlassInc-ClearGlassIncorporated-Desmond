"use client";

import { AnimatedSection } from "./AnimatedSection";
import { MagneticButton } from "./MagneticButton";

interface Scene {
  readonly num: string;
  readonly title: string;
  readonly copy: string;
  readonly items: readonly string[];
  readonly scatter: boolean;
}

const SCENES: readonly Scene[] = [
  { num: "01", title: "Fragmentation", copy: "Most digital systems are built in fragments.", items: ["Website", "Content", "Data", "Leads", "Automation", "Security", "Analytics"], scatter: true },
  { num: "02", title: "Architecture", copy: "ClearGlass connects the pieces into a system.", items: ["Strategy", "Experience", "Infrastructure", "Measurement", "Optimization"], scatter: false },
  { num: "03", title: "Activation", copy: "Every interaction becomes a measurable opportunity to improve.", items: ["Discover", "Engage", "Convert", "Learn", "Improve"], scatter: false },
  { num: "04", title: "Growth infrastructure", copy: "Your website becomes more than a destination. It becomes growth infrastructure.", items: [], scatter: false },
];

/** Deterministic scatter offsets, seeded by index. */
function offset(i: number): React.CSSProperties {
  const a = Math.sin(i * 12.9898) * 43758.5453;
  const b = Math.sin(i * 78.233) * 12345.6789;
  const fx = ((a - Math.floor(a)) * 2 - 1) * 44;
  const fy = ((b - Math.floor(b)) * 2 - 1) * 30;
  const fr = ((a - Math.floor(a)) * 2 - 1) * 5;
  return {
    "--cgm-fx": `${fx.toFixed(1)}px`,
    "--cgm-fy": `${fy.toFixed(1)}px`,
    "--cgm-fr": `${fr.toFixed(2)}deg`,
  } as React.CSSProperties;
}

/**
 * Four stacked scenes. Ordinary document flow — no pinning, no scroll
 * hijacking, no scrollTo — so keyboard, touch and browser history behave
 * exactly as they would without it.
 */
export function ScrollNarrative(): React.JSX.Element {
  return (
    <>
      {SCENES.map((scene, index) => (
        <AnimatedSection
          key={scene.num}
          index={index}
          id={`cgm-scene-${scene.num}`}
          className={scene.scatter ? "cgm-scene cgm-scene--scatter" : "cgm-scene"}
          aria-labelledby={`cgm-scene-${scene.num}-h`}
        >
          <div className="cgm-shell">
            <p className="cgm-eyebrow">
              Scene {scene.num} — {scene.title}
            </p>
            <h2 id={`cgm-scene-${scene.num}-h`} className="cgm-display">
              {scene.copy}
            </h2>
            {scene.items.length > 0 ? (
              <ul className="cgm-frags">
                {scene.items.map((item, i) => (
                  <li key={item} className="cgm-frag" style={offset(i)}>
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="cgm-actions">
                <MagneticButton href="/contact" withArrow>
                  Build the system
                </MagneticButton>
              </p>
            )}
          </div>
        </AnimatedSection>
      ))}
    </>
  );
}
