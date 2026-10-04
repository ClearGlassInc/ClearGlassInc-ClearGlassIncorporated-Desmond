# ClearGlass Intelligence Graph — Executive UI Specification

Status: implementation branch feat/intelligence-graph-executive-ui.

## 1. Dashboard wireframe

~~~
┌─────────────────────────────────────────────────────────────────────────────┐
│ ClearGlass  Intelligence Graph             Evidence-aware   Summary  Fullscreen│
├─────────────────────────────────────────────────────────────────────────────┤
│ Intelligence score     Threat status       Confidence        Last updated  │
│      —                 Not assessed             —                  —         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Active models │ Nodes │ Relationships │ Density │ Coverage                 │
├───────────────────────────────────────────────┬─────────────────────────────┤
│                                               │ Integrity                   │
│  Relationship graph                           │ Executive readout           │
│  [search] [filters] [zoom fit verify]         │ AI findings                │
│                                               │ Recommended actions         │
│             interactive Sigma graph            │ Top risks                   │
│                                               │ Source coverage             │
│                                               │ Analyst query               │
├───────────────────────────────────────────────┴─────────────────────────────┤
│ Observation feed                         │ Entity inspector                  │
├────────────────────────────────────────────┴────────────────────────────────┤
│ Analytical diagnostics                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
~~~

On mobile the hierarchy becomes: hero status → key metrics → graph → executive rail → observations → inspector → diagnostics.

## 2. Component hierarchy

- cg-shell
  - sticky header / navigation
  - command status strip
  - key metric grid
  - workspace
    - graph panel
      - graph top bar
      - search/filter toolbar
      - Sigma canvas
      - graph legend / breadcrumb
    - executive rail
      - integrity
      - executive readout
      - governed AI findings
      - recommended actions
      - top risks
      - source coverage
      - analyst query
  - lower intelligence grid
    - observation feed
    - entity inspector
  - diagnostics
  - one-tap executive summary modal

## 3. Typography system

- Primary: Inter, with system fallbacks.
- Executive metric: 32–54px, 800 weight, tight tracking.
- Panel headings: 15–20px, 700–800.
- Body: 12–13px, line-height 1.45–1.6.
- UI labels: 10–11px, semibold; sentence case preferred.
- Machine-readable values and query text: system monospace.
- Avoid decorative all-caps except compact status labels.

## 4. Colour system

- Graphite/base: #07080b / #0b0c11.
- ClearGlass crimson: #c4363a.
- Bright crimson: #eb4344.
- Wine: #7a123d.
- Cyan accent: #67e8f9.
- Teal success: #5ef2b5.
- Amber caution: #f4b860.
- Primary text: #f7f2f2.
- Muted text: #bcaeb0.
- Dim text: #8b7d81.
- Danger: #ff7b80.
- Glow is used only on status/control emphasis; glassmorphism is limited to major overlays and the graph empty-state.

## 5. Mobile layout

- 1-column flow.
- Touch targets are at least 38px high, with 42px action controls where practical.
- Sticky header provides Summary / Full screen / Close.
- Hero metric becomes full-width; threat/confidence/updated cards share the next row.
- Metric cards use a 2-column grid.
- Graph remains the primary interaction surface and keeps controls inside the thumb-reachable toolbar.
- Executive modules become stacked, not hidden.
- Observation and diagnostics stay below the decision surface.
- prefers-reduced-motion is honored.

## 6. Desktop layout

- 5-up key metric strip.
- Graph workspace uses a dominant left canvas and a fixed-width executive rail.
- Rail scrolls independently when the graph is tall.
- Observation feed and inspector form a secondary row.
- Diagnostics are full-width and progressively disclosed below the decision surface.
- Full-screen graph mode uses the existing Sigma renderer rather than introducing a second renderer.

## 7. Dashboard mockup description

Visual direction: premium ClearGlass crimson-and-graphite command console, with restrained cyan/teal/amber accents. The main graph sits inside a deep graphite canvas with a subtle technical grid; crimson is reserved for brand emphasis and severity, cyan for active analysis, teal for verification, and amber for caution. The interface is analytical rather than cinematic: clear numbers, short labels, visible provenance, and no decorative sci-fi chrome that competes with the graph.

## 8. Tailwind CSS design tokens

~~~
theme: {
  extend: {
    colors: {
      cg: {
        bg: "#07080b",
        panel: "#101014",
        crimson: "#c4363a",
        bright: "#eb4344",
        wine: "#7a123d",
        cyan: "#67e8f9",
        teal: "#5ef2b5",
        amber: "#f4b860",
        text: "#f7f2f2",
        muted: "#bcaeb0",
        dim: "#8b7d81",
        danger: "#ff7b80"
      }
    },
    transitionDuration: {
      cg: "160ms"
    }
  }
}
~~~

## 9. React component structure

~~~
IntelligenceGraphPage
├── IntelligenceHeader
├── StatusStrip
│   ├── IntelligenceScore
│   ├── ThreatStatus
│   ├── ConfidenceCard
│   └── LastUpdated
├── MetricGrid
├── IntelligenceWorkspace
│   ├── GraphPanel
│   │   ├── GraphToolbar
│   │   ├── SigmaCanvas
│   │   └── GraphBreadcrumb
│   └── ExecutiveRail
│       ├── IntegrityCard
│       ├── ExecutiveReadout
│       ├── AIFindings
│       ├── RecommendedActions
│       ├── TopRisks
│       ├── SourceCoverage
│       └── AnalystQuery
├── ObservationFeed
├── EntityInspector
└── AnalyticalDiagnostics
~~~

For the current static site, these responsibilities remain implemented as DOM sections and the existing Sigma renderer; this structure is the migration target, not a forced framework rewrite.

## 10. Accessibility recommendations

- Preserve semantic headings and landmarks.
- Maintain visible keyboard focus states.
- Use aria-live for integrity status and alerts.
- Keep contrast at or above AAA targets where technically practical; never rely on accent colour alone.
- Pair severity colour with text labels and icons.
- Use aria-pressed for sector filters.
- Keep search, filter, zoom, fit, verify and full-screen controls keyboard accessible.
- Do not expose synthetic intelligence scores when evidence is absent.
- Announce blocked states through role=alert.
- Honour prefers-reduced-motion.
- Provide a readable inspector/provenance path even when graph visual rendering is unavailable.
