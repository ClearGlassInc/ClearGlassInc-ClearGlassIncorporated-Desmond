"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CameraAsset, FlightAsset, LiveOpsResponse, SatelliteAsset, SourceHealth } from "@/lib/live-ops/types";
import styles from "./chualar.module.css";

type LayerKey = "flights" | "military" | "satellites" | "cctv";
type Selected = { kind: LayerKey; asset: FlightAsset | SatelliteAsset | CameraAsset } | null;
const CENTER = { lat: 36.57, lon: -121.525 };
const INITIAL_LAYERS: Record<LayerKey, boolean> = { flights: true, military: true, satellites: true, cctv: true };
const names: Record<LayerKey, string> = { flights: "LIVE FLIGHTS", military: "MILITARY FLIGHTS", satellites: "SATELLITES", cctv: "CCTV" };
const colors: Record<LayerKey, string> = { flights: "#41e8ff", military: "#ff665f", satellites: "#b18aff", cctv: "#60e6a6" };
const emptyData: LiveOpsResponse = {
  generated_at: "", area: { center: CENTER, radius_nm: 40, bounds: { lamin: 0, lomin: 0, lamax: 0, lomax: 0 } },
  counts: { live_flights: null, military_flights: null, satellites: null, cctv: null, total_assets: null },
  layers: { flights: [], military: [], satellites: [], cctv: [] },
  sources: { flights: "offline", military: "offline", satellites: "offline", cctv: "offline" }, errors: {}
};
function sourceLabel(v: SourceHealth) { return v.toUpperCase(); }
function countLabel(n: number | null) { return n === null ? "—" : n.toLocaleString(); }
function mapPoint(lat: number, lon: number, zoom: number) {
  const center = webMercatorPixels(CENTER.lat, CENTER.lon, zoom);
  const point = webMercatorPixels(lat, lon, zoom);
  const worldSpan = 256 * 3;
  return {
    x: 50 + (point.x - center.x) / worldSpan * 100,
    y: 50 + (point.y - center.y) / worldSpan * 100
  };
}
export default function ChualarOperations(): React.JSX.Element {
  const [data, setData] = useState<LiveOpsResponse>(emptyData);
  const [layers, setLayers] = useState(INITIAL_LAYERS);
  const [selected, setSelected] = useState<Selected>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [radius, setRadius] = useState(40);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const lastGood = useRef<LiveOpsResponse | null>(null);
  const refresh = useCallback(async (manual = false) => {
    if (busyRef.current && !manual) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const query = new URLSearchParams({ lat: String(CENTER.lat), lon: String(CENTER.lon), radius_nm: String(radius) });
      const response = await fetch(`/api/live/ops?${query}`, { cache: "no-store", headers: { accept: "application/json" } });
      if (!response.ok) throw new Error(response.status === 429 ? "Request limit reached; waiting for the next refresh." : `Operations API returned HTTP ${response.status}.`);
      const next = await response.json() as LiveOpsResponse;
      if (!next || !next.layers || !next.sources) throw new Error("Operations API returned an invalid payload.");
      setData(next); lastGood.current = next; setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed.");
      if (!lastGood.current) setData(emptyData);
      else setData({ ...lastGood.current, sources: { ...lastGood.current.sources, flights: lastGood.current.sources.flights === "online" ? "degraded" : lastGood.current.sources.flights, military: lastGood.current.sources.military === "online" ? "degraded" : lastGood.current.sources.military, satellites: lastGood.current.sources.satellites === "online" ? "degraded" : lastGood.current.sources.satellites, cctv: lastGood.current.sources.cctv === "online" ? "degraded" : lastGood.current.sources.cctv } });
    } finally { busyRef.current = false; setBusy(false); }
  }, [radius]);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => void refresh(), 10_000);
    return () => window.clearInterval(id);
  }, [autoRefresh, refresh]);

  const assets = useMemo(() => ({
    flights: data.layers.flights.map(asset => ({ kind: "flights" as const, asset })),
    military: data.layers.military.map(asset => ({ kind: "military" as const, asset })),
    satellites: data.layers.satellites.map(asset => ({ kind: "satellites" as const, asset })),
    cctv: data.layers.cctv.map(asset => ({ kind: "cctv" as const, asset }))
  }), [data]);
  const allMarkers = (Object.keys(assets) as LayerKey[]).flatMap(kind => layers[kind] ? assets[kind].map(({ asset }) => ({ kind, asset })) : []);
  const sourceStatus = data.sources;
  const viewRadius = useMemo(() => {
    const nearby = layers.satellites
      ? data.layers.satellites.filter(asset => asset.context === "NEARBY")
        .map(asset => distanceNm(CENTER, asset.lat, asset.lon) * 1.05)
      : [];
    return Math.max(radius, ...nearby);
  }, [data.layers.satellites, layers.satellites, radius]);
  const tileLayout = useMemo(() => {
    const zoom = tileZoomForRadius(CENTER.lat, viewRadius);
    const centerPx = webMercatorPixels(CENTER.lat, CENTER.lon, zoom);
    const minX = Math.floor((centerPx.x - 384) / 256);
    const maxX = Math.floor((centerPx.x + 384) / 256);
    const minY = Math.floor((centerPx.y - 384) / 256);
    const maxY = Math.floor((centerPx.y + 384) / 256);
    const worldTiles = 2 ** zoom;
    const tiles: Array<{ key: string; url: string; left: number; top: number }> = [];
    for (let y = minY; y <= maxY; y += 1) {
      if (y < 0 || y >= worldTiles) continue;
      for (let x = minX; x <= maxX; x += 1) {
        const wrappedX = ((x % worldTiles) + worldTiles) % worldTiles;
        tiles.push({
          key: zoom + "/" + wrappedX + "/" + y,
          url: "https://tile.openstreetmap.org/" + zoom + "/" + wrappedX + "/" + y + ".png",
          left: 50 + (x * 256 - centerPx.x) / 768 * 100,
          top: 50 + (y * 256 - centerPx.y) / 768 * 100
        });
      }
    }
    return { zoom, tiles };
  }, [viewRadius]);
  const radiusRingPct = Math.min(96, (2 * radius * 1.852) / (3 * (40075.016686 * Math.cos(CENTER.lat * Math.PI / 180) / (2 ** tileLayout.zoom))) * 100);
  function toggle(kind: LayerKey) { setLayers(prev => ({ ...prev, [kind]: !prev[kind] })); }
  function titleFor(kind: LayerKey, asset: FlightAsset | SatelliteAsset | CameraAsset): string {
    if (kind === "satellites") return (asset as SatelliteAsset).name;
    if (kind === "cctv") return (asset as CameraAsset).name;
    return (asset as FlightAsset).callsign || (asset as FlightAsset).icao24;
  }
  return <main className={styles.shell}>
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>CLEARGLASS / PUBLIC-SOURCE SENSOR FABRIC</p><h1>CHUALAR <span>— MONTEREY COUNTY</span><br/>LIVE OPERATIONS</h1><p className={styles.sub}>36.5700° N · 121.5250° W · {radius} NM OPERATIONAL RADIUS</p></div>
      <div className={styles.live}><span className={styles.pulse}/><strong>LIVE</strong><small>{busy ? "SYNCING" : "POLLING / 10 SEC"}</small></div>
    </header>
    <section className={styles.toolbar}>
      <label>RADIUS <select value={radius} onChange={e => setRadius(Number(e.target.value))}><option value={20}>20 NM</option><option value={40}>40 NM</option><option value={60}>60 NM</option><option value={100}>100 NM</option><option value={150}>150 NM</option></select></label>
      <label className={styles.auto}><input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}/> AUTO REFRESH</label>
      <button onClick={() => void refresh(true)} disabled={busy}>{busy ? "REFRESHING…" : "↻ REFRESH NOW"}</button>
      <span className={styles.updated}>LAST RESPONSE: {data.generated_at ? new Date(data.generated_at).toLocaleTimeString() : "—"}</span>
    </section>
    {error && <div role="alert" className={styles.error}><strong>DATA REFRESH WARNING</strong> {error} {lastGood.current ? "Showing last good response where available." : "No previous response is available."}</div>}
    <section className={styles.layerGrid} aria-label="Independent map layers">
      {(Object.keys(names) as LayerKey[]).map(kind => {
        const count = kind === "flights" ? data.counts.live_flights : kind === "military" ? data.counts.military_flights : kind === "satellites" ? data.counts.satellites : data.counts.cctv;
        const status = sourceStatus[kind];
        return <button type="button" key={kind} className={`${styles.layerCard} ${layers[kind] ? styles.layerActive : ""}`} onClick={() => toggle(kind)} aria-pressed={layers[kind]} style={{ "--layer-color": colors[kind] } as React.CSSProperties}>
          <span className={styles.layerTop}><i/> <span>{names[kind]}</span><b>{layers[kind] ? "ON" : "OFF"}</b></span>
          <strong className={styles.count}>{countLabel(count)}</strong><span className={styles.cardFoot}><span className={`${styles.status} ${styles[status]}`}>{sourceLabel(status)}</span><span>{kind === "cctv" ? "PUBLIC CAMERAS" : kind === "satellites" ? "TRACKED OBJECTS" : "AIRCRAFT"}</span></span>
        </button>;
      })}
    </section>
    <section className={styles.contentGrid}>
      <div className={styles.mapPanel}>
        <div className={styles.panelHeading}><div><h2>GEOSPATIAL TRACK VIEW</h2><p>Configured operational radius · schematic projection</p></div><span>{allMarkers.length.toLocaleString()} VISIBLE ASSETS</span></div>
        <div className={styles.map} role="group" aria-label="Interactive OpenStreetMap view with live-source asset markers">
          <div className={styles.mapSurface}>
            {tileLayout.tiles.map(tile => <img key={tile.key} className={styles.mapTile} src={tile.url} alt="" aria-hidden="true" loading="lazy" referrerPolicy="strict-origin-when-cross-origin" style={{ left: tile.left + "%", top: tile.top + "%" }}/>)}
            <div className={styles.gridLines}/>
            <div className={styles.ring + " " + styles.ring1} style={{ width: radiusRingPct / 2 + "%" }}/>
            <div className={styles.ring + " " + styles.ring2} style={{ width: radiusRingPct + "%" }}/>
            <div className={styles.centerMark}><b/>CHUALAR</div>
            {allMarkers.map(({ kind, asset }) => {
              const point = mapPoint(asset.lat, asset.lon, tileLayout.zoom);
              if (point.x < 0 || point.x > 100 || point.y < 0 || point.y > 100) return null;
              const markerTitle = titleFor(kind, asset);
              return <button key={kind + ":" + asset.id} type="button" title={markerTitle} className={styles.marker + " " + styles["marker_" + kind]} style={{ left: point.x + "%", top: point.y + "%" }} onClick={() => setSelected({ kind, asset })} aria-label={"Select " + names[kind] + " asset " + markerTitle}>{kind === "flights" ? "✈" : kind === "military" ? "◆" : kind === "satellites" ? "✦" : "●"}</button>;
            })}
            {!allMarkers.length && <div className={styles.emptyMap}>NO ASSETS TO PLOT<br/><span>Sources may be offline, unavailable, or empty for this radius.</span></div>}
          </div>
          <div className={styles.mapLegend}>{(Object.keys(names) as LayerKey[]).filter(k => layers[k]).map(k => <span key={k}><i style={{ background: colors[k] }}/>{names[k]}</span>)}</div>
          <div className={styles.scale}>N ↑ <span>{radius} NM OPERATIONAL RADIUS</span></div>
          <a className={styles.attribution} href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a>
        </div>
        <p className={styles.mapNote}>Markers use provider coordinates over an OpenStreetMap basemap. Public tile availability is best-effort; missing source positions are never inferred.</p>
      </div>
      <aside className={styles.sidePanel}>
        <div className={styles.panelHeading}><div><h2>ASSET INSPECTOR</h2><p>Choose any plotted marker</p></div></div>
        {selected ? <AssetDetails selected={selected}/> : <div className={styles.inspectEmpty}> <span>◎</span><strong>NO ASSET SELECTED</strong><p>Select a visible map marker to inspect source fields and the latest provider timestamp.</p></div>}
        <div className={styles.health}><h3>PROVIDER HEALTH</h3>{(Object.keys(names) as LayerKey[]).map(k => <div className={styles.healthRow} key={k}><span><i style={{ background: colors[k] }}/>{names[k]}</span><b className={styles[sourceStatus[k]]}>{sourceLabel(sourceStatus[k])}</b>{data.errors[k] && <p>{data.errors[k]}</p>}</div>)}</div>
      </aside>
    </section>
    <footer className={styles.footer}>PUBLIC-SOURCE DATA ONLY · COUNTS ARE RESPONSE COUNTS, NOT TARGET BADGES · PROVIDER AVAILABILITY AND LATENCY VARY · NO OPERATIONAL INFERENCE</footer>
  </main>;
}
function AssetDetails({ selected }: { selected: NonNullable<Selected> }): React.JSX.Element {
  const { kind, asset } = selected;
  const row = (label: string, value: unknown) => <div className={styles.detailRow} key={label}><span>{label}</span><strong>{value === null || value === undefined || value === "" ? "—" : String(value)}</strong></div>;
  if (kind === "flights" || kind === "military") {
    const a = asset as FlightAsset;
    return <div className={styles.details}><p className={styles.assetType} style={{ color: colors[kind] }}>{kind === "military" ? "MILITARY AIRCRAFT · PUBLIC PROVIDER FLAG" : "AIRCRAFT TRACK"}</p><h3>{a.callsign || a.icao24}</h3>{row("ICAO24", a.icao24)}{row("ALTITUDE", a.altitude_ft === null ? null : `${a.altitude_ft.toLocaleString()} ft`)}{row("GROUND SPEED", a.speed_kts === null ? null : `${a.speed_kts} kt`)}{row("HEADING", a.heading_deg === null ? null : `${a.heading_deg}°`)}{row("SQUAWK", a.squawk)}{row("COUNTRY", a.country)}{row("OPERATOR", a.operator)}{row("ON GROUND", a.on_ground === null ? null : a.on_ground ? "YES" : "NO")}{row("VERTICAL RATE", a.vertical_rate === null ? null : `${a.vertical_rate} ft/min`)}{row("LAST SEEN", a.last_seen ? new Date(a.last_seen).toLocaleString() : null)}</div>;
  }
  if (kind === "satellites") {
    const a = asset as SatelliteAsset;
    return <div className={styles.details}><p className={styles.assetType} style={{ color: colors.satellites }}>SATELLITE · {a.context}</p><h3>{a.name}</h3>{row("NORAD ID", a.norad_id)}{row("ALTITUDE", a.altitude_km === null ? null : `${a.altitude_km.toLocaleString()} km`)}{row("VELOCITY", a.velocity_kms === null ? null : `${a.velocity_kms} km/s`)}{row("AZIMUTH", a.azimuth === null ? null : `${a.azimuth}°`)}{row("ELEVATION", a.elevation === null ? null : `${a.elevation}°`)}{row("POSITION TIME", a.last_seen ? new Date(a.last_seen).toLocaleString() : null)}<p className={styles.detailNote}>N2YO /above provides position and altitude. Velocity, azimuth, elevation and next-pass are shown only when a provider response supplies them.</p></div>;
  }
  const a = asset as CameraAsset;
  return <div className={styles.details}><p className={styles.assetType} style={{ color: colors.cctv }}>PUBLIC TRAFFIC CAMERA</p><h3>{a.name}</h3>{row("AGENCY", a.agency)}{row("STATUS", a.status)}{row("LAST CHECKED", new Date(a.last_checked).toLocaleString())}{a.preview_url && <><a className={styles.cameraLink} href={a.preview_url} target="_blank" rel="noreferrer">OPEN PREVIEW ↗</a><a className={styles.previewFrame} href={a.preview_url} target="_blank" rel="noreferrer"><img src={a.preview_url} alt={`Public preview for ${a.name}`} loading="lazy" referrerPolicy="no-referrer"/><span>PUBLIC CAMERA PREVIEW · OPEN FULL SIZE</span></a></>}{a.stream_url && <a className={styles.cameraLink} href={a.stream_url} target="_blank" rel="noreferrer">OPEN STREAM ↗</a>}{a.page_url && <a className={styles.cameraLink} href={a.page_url} target="_blank" rel="noreferrer">OFFICIAL SOURCE PAGE ↗</a>}</div>;
}
