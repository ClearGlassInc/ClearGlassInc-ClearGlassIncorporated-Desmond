import type { Metadata } from "next";
import {
  AnimatedSection,
  CapabilityConstellation,
  CinematicPageShell,
  GlassCard,
  GlassPrism,
  GrowthSystemMap,
  LiveSignalBadge,
  MagneticButton,
  ReducedMotionFallback,
  ScrollNarrative,
} from "@/components/motion";

export const metadata: Metadata = {
  title: "Motion system — ClearGlass Inc.",
  description:
    "The ClearGlass cinematic motion system: hero interface, capability constellation and scroll narrative.",
};

const HERO_NODES: readonly { label: string; copy: string }[] = [
  { label: "Attention", copy: "Being seen by the right people, in the places they already look." },
  { label: "Trust", copy: "Evidence, provenance and clarity that let a stranger believe you." },
  { label: "Conversion", copy: "Turning understanding into a booked, qualified conversation." },
  { label: "Performance", copy: "Speed and stability, because neither trust nor ranking survives a slow page." },
  { label: "Search", copy: "Technical discoverability: structure, schema and internal authority." },
  { label: "Automation", copy: "Governed workflows that remove manual steps, not human approval." },
  { label: "Security", copy: "Header posture, dependency integrity and an auditable trail." },
  { label: "Learning", copy: "Measurement that closes the loop and improves the next cycle." },
];

const SERVICES: readonly { name: string; copy: string }[] = [
  { name: "Digital strategy", copy: "Positioning and sequencing — deciding what to build before building it." },
  { name: "Web design & development", copy: "Interface, narrative and a typed, accessible, maintainable build." },
  { name: "AI automation", copy: "Model-assisted workflows under read-only analysis, draft, approval, log." },
  { name: "Cybersecurity", copy: "Threat modelling, edge posture and evidence an auditor accepts." },
  { name: "DevSecOps", copy: "Pipelines that gate on tests and policy rather than on good intentions." },
  { name: "SEO & discoverability", copy: "Structure, schema and link authority that compound over quarters." },
  { name: "Data integration", copy: "Contracts between systems, validated at the boundary." },
  { name: "Growth infrastructure", copy: "The connective layer that makes the rest measurable." },
];

export default function MotionSystemPage(): React.JSX.Element {
  return (
    <CinematicPageShell>
      <AnimatedSection
        id="cgm-hero"
        className="cgm-scene"
        aria-labelledby="cgm-hero-h"
      >
        <div className="cgm-shell">
          <GlassPrism />
          <p className="cgm-eyebrow">Growth Infrastructure Interface</p>
          <h1 id="cgm-hero-h" className="cgm-display">
            Build a digital system that compounds attention, trust, and growth.
          </h1>
          <p className="cgm-lede">
            ClearGlass Inc. designs high-performance websites and intelligent digital
            systems that connect strategy, engineering, automation, discoverability,
            analytics, and security-conscious architecture.
          </p>
          <p className="cgm-actions">
            <MagneticButton href="/contact" withArrow>
              Engineer my growth system
            </MagneticButton>
            <a className="cgm-btn cgm-btn--secondary" href="#cgm-constellation-h">
              Explore the system
            </a>
          </p>
          <ul className="cgm-grid">
            {HERO_NODES.map((node) => (
              <li key={node.label}>
                <GlassCard>
                  <h3>{node.label}</h3>
                  <p>{node.copy}</p>
                </GlassCard>
              </li>
            ))}
          </ul>
          <p className="cgm-illustrative">
            Interactive demonstration — illustrative data only.
          </p>
        </div>
      </AnimatedSection>

      <AnimatedSection className="cgm-scene" aria-labelledby="cgm-constellation-h">
        <div className="cgm-shell">
          <p className="cgm-eyebrow">Capability constellation</p>
          <h2 id="cgm-constellation-h" className="cgm-display">
            Nine capabilities, one system.
          </h2>
          <p className="cgm-lede">
            Select two or more capabilities to trace an engagement pathway. Every node
            is keyboard reachable and carries its own written explanation.
          </p>
          {/* Reduced motion gets the same graph as a static diagram, not a gap. */}
          <ReducedMotionFallback
            fallback={
              <div className="cgm-constellation">
                <div className="cgm-stage">
                  <GrowthSystemMap title="ClearGlass capability graph (static view)" />
                </div>
                <div className="cgm-readout">
                  <h3>Operations</h3>
                  <p>
                    The connective layer: runbooks, ownership, escalation and the boring
                    reliability work that compounds.
                  </p>
                </div>
              </div>
            }
          >
            <CapabilityConstellation />
          </ReducedMotionFallback>
        </div>
      </AnimatedSection>

      <AnimatedSection className="cgm-scene" aria-labelledby="cgm-services-h">
        <div className="cgm-shell">
          <p className="cgm-eyebrow">
            Capabilities <LiveSignalBadge state="healthy" detail="all systems nominal" />
          </p>
          <h2 id="cgm-services-h" className="cgm-display">
            What we build.
          </h2>
          <ul className="cgm-grid">
            {SERVICES.map((service) => (
              <li key={service.name}>
                <GlassCard tilt trace>
                  <h3>{service.name}</h3>
                  <p>{service.copy}</p>
                </GlassCard>
              </li>
            ))}
          </ul>
        </div>
      </AnimatedSection>

      <ScrollNarrative />
    </CinematicPageShell>
  );
}
