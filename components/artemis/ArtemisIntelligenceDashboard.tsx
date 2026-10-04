const modules = [
  ["Situation Room", "Cross-source executive situational awareness"],
  ["Global Operations Map", "OSM basemap + normalized events/observations"],
  ["Aviation Layer", "Licensed aircraft feeds only"],
  ["Maritime Layer", "Licensed vessel feeds only"],
  ["Weather Layer", "Weather + lightning + hazard context"],
  ["Earthquake Layer", "USGS GeoJSON events and alerts"],
  ["Space Layer", "NASA APOD + NASA Images + astronomy references"],
  ["Environmental Monitoring", "GFW + environmental datasets"],
  ["Historical Archive Explorer", "Internet Archive + Gutenberg + Open Library + LoC"],
  ["Data Explorer", "OWID + World Bank + Gapminder + statistics"],
  ["Intelligence Reports", "Provenance-backed analyst outputs"],
];

const phaseOne = [
  "OpenStreetMap",
  "USGS Earthquake Feed",
  "NASA APOD",
  "NASA Image Library",
  "Our World in Data",
  "World Bank Open Data",
];

export function ArtemisIntelligenceDashboard() {
  return (
    <main style={{ minHeight: "100vh", background: "#05070c", color: "#e8edf7", padding: "32px" }}>
      <section style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start" }}>
          <div>
            <p style={{ letterSpacing: "0.18em", fontSize: 12, opacity: 0.7, margin: 0 }}>CLEARGLASS · ARTEMIS / AEGIS</p>
            <h1 style={{ fontSize: "clamp(36px, 6vw, 72px)", lineHeight: 0.95, margin: "14px 0" }}>See Through Everything</h1>
            <p style={{ maxWidth: 720, opacity: 0.78, fontSize: 17 }}>
              Unified public-source intelligence fabric with attribution, auditability, geospatial normalization and fail-closed connector boundaries.
            </p>
          </div>
          <div style={{ border: "1px solid rgba(255,255,255,.14)", borderRadius: 18, padding: 16, minWidth: 200 }}>
            <div style={{ fontSize: 11, opacity: 0.65 }}>FABRIC STATUS</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginTop: 8 }}>READY</div>
            <div style={{ fontSize: 12, opacity: 0.65, marginTop: 5 }}>30 registered sources</div>
          </div>
        </div>

        <div style={{ marginTop: 32, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 14 }}>
          {modules.map(([name, description]) => (
            <article key={name} style={{ border: "1px solid rgba(255,255,255,.11)", borderRadius: 16, padding: 18, background: "rgba(255,255,255,.035)" }}>
              <h2 style={{ margin: 0, fontSize: 17 }}>{name}</h2>
              <p style={{ margin: "8px 0 0", opacity: 0.66, fontSize: 13, lineHeight: 1.5 }}>{description}</p>
            </article>
          ))}
        </div>

        <section style={{ marginTop: 28, border: "1px solid rgba(255,255,255,.11)", borderRadius: 16, padding: 20 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.12em", opacity: 0.65 }}>PHASE 1 · ENABLED BY DEFAULT</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 14 }}>
            {phaseOne.map((source) => (
              <span key={source} style={{ borderRadius: 999, padding: "8px 12px", background: "rgba(64,170,255,.10)", border: "1px solid rgba(64,170,255,.25)", fontSize: 12 }}>
                {source}
              </span>
            ))}
          </div>
          <p style={{ margin: "16px 0 0", opacity: 0.58, fontSize: 12 }}>
            Commercial and web-only providers remain registered but disabled until API contracts, licensing, rate limits and redistribution rights are verified.
          </p>
        </section>
      </section>
    </main>
  );
}
