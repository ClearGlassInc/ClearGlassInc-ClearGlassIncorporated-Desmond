export type SourceHealth = "online" | "degraded" | "offline";
export type AssetType = "flight" | "satellite" | "cctv";

export interface Bounds {
  lamin: number; lomin: number; lamax: number; lomax: number;
}
export interface Center { lat: number; lon: number; }
export interface FlightAsset {
  id: string; type: "flight"; lat: number; lon: number;
  altitude_ft: number | null; speed_kts: number | null; heading_deg: number | null;
  callsign: string | null; icao24: string; country: string | null; operator?: string | null; squawk: string | null;
  on_ground: boolean | null; vertical_rate: number | null; last_seen: string | null;
  category?: "military" | number | null;
}
export interface SatelliteAsset {
  id: string; type: "satellite"; name: string; norad_id: string; lat: number; lon: number;
  altitude_km: number | null; velocity_kms: number | null; azimuth: number | null;
  elevation: number | null; last_seen: string | null; context: "OVERHEAD" | "NEARBY";
}
export interface CameraAsset {
  id: string; type: "cctv"; name: string; agency: string; lat: number; lon: number;
  status: "online" | "offline" | "unknown"; preview_url: string | null;
  stream_url: string | null; page_url: string | null; last_checked: string;
}
export interface ProviderResult<T> { items: T[]; status: SourceHealth; error?: string; stale?: boolean; }
export interface LiveOpsResponse {
  generated_at: string;
  area: { center: Center; radius_nm: number; bounds: Bounds; };
  counts: { live_flights: number | null; military_flights: number | null; satellites: number | null; cctv: number | null; total_assets: number | null; };
  layers: { flights: FlightAsset[]; military: FlightAsset[]; satellites: SatelliteAsset[]; cctv: CameraAsset[]; };
  sources: { flights: SourceHealth; military: SourceHealth; satellites: SourceHealth; cctv: SourceHealth; };
  errors: Partial<Record<"flights" | "military" | "satellites" | "cctv", string>>;
}
export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function parseFiniteNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isValidCoordinates(lat: number, lon: number): boolean {
  return Number.isFinite(lat) && lat >= -90 && lat <= 90 &&
    Number.isFinite(lon) && lon >= -180 && lon <= 180;
}

export interface MercatorPoint { x: number; y: number; }

export function webMercatorPixels(lat: number, lon: number, zoom: number): MercatorPoint {
  const safeLat = Math.max(-85.05112878, Math.min(85.05112878, lat));
  const worldSize = 256 * 2 ** zoom;
  const sinLat = Math.sin(safeLat * Math.PI / 180);
  return {
    x: ((lon + 180) / 360) * worldSize,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * worldSize,
  };
}

export function tileZoomForRadius(centerLat: number, radiusNm: number): number {
  const radiusKm = radiusNm * 1.852;
  const targetTileKm = (2 * radiusKm) / 2.25;
  const latitudeAdjustedWorldKm = 40075.016686 * Math.cos(centerLat * Math.PI / 180);
  const zoom = Math.round(Math.log2(latitudeAdjustedWorldKm / targetTileKm));
  return Math.max(3, Math.min(13, zoom));
}
export function cleanText(value: unknown, max = 120): string | null {
  if (typeof value !== "string") return null;
  const text = value.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, max);
  return text || null;
}
export function inBounds(lat: number, lon: number, b: Bounds): boolean {
  if (!isValidCoordinates(lat, lon) || lat < b.lamin || lat > b.lamax) return false;
  // lomin > lomax represents a box crossing the antimeridian.
  return b.lomin <= b.lomax
    ? lon >= b.lomin && lon <= b.lomax
    : lon >= b.lomin || lon <= b.lomax;
}
export function distanceNm(a: Center, lat: number, lon: number): number {
  const rad = (n: number) => n * Math.PI / 180;
  const dLat = rad(lat - a.lat), dLon = rad(lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(lat)) * Math.sin(dLon / 2) ** 2;
  return 3440.065 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}
export function boundsFor(center: Center, radiusNm: number): Bounds {
  if (!isValidCoordinates(center.lat, center.lon) || !Number.isFinite(radiusNm) || radiusNm <= 0) {
    throw new RangeError("Invalid geospatial center or radius");
  }
  const dLat = radiusNm / 60;
  const dLon = radiusNm / (60 * Math.max(0.1, Math.cos(center.lat * Math.PI / 180)));
  // If the longitude span covers the globe, represent it with a conventional full-width box.
  if (dLon >= 180) return { lamin: Math.max(-90, center.lat - dLat), lomin: -180, lamax: Math.min(90, center.lat + dLat), lomax: 180 };
  const wrap = (lon: number) => ((lon + 180) % 360 + 360) % 360 - 180;
  return {
    lamin: Math.max(-90, center.lat - dLat),
    lomin: wrap(center.lon - dLon),
    lamax: Math.min(90, center.lat + dLat),
    lomax: wrap(center.lon + dLon)
  };
}

/** Runtime shape guard for the complete normalized API response received by the browser. */
export function isLiveOpsResponse(value: unknown): value is LiveOpsResponse {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  const obj = (x: unknown): x is Record<string, unknown> =>
    Boolean(x) && typeof x === "object" && !Array.isArray(x);
  const finiteOrNull = (x: unknown) => x === null || isFiniteNumber(x);
  const validTime = (x: unknown) => typeof x === "string" && Number.isFinite(Date.parse(x));
  if (!validTime(v.generated_at) || !obj(v.area) || !obj(v.layers) || !obj(v.sources) ||
      !obj(v.counts) || !obj(v.errors)) return false;

  const area = v.area as Record<string, unknown>;
  const layers = v.layers as Record<string, unknown>;
  const sources = v.sources as Record<string, unknown>;
  const counts = v.counts as Record<string, unknown>;
  if (!obj(area.center) || !obj(area.bounds)) return false;
  const center = area.center as Record<string, unknown>;
  const b = area.bounds as Record<string, unknown>;
  if (!isFiniteNumber(center.lat) || !isFiniteNumber(center.lon) ||
      !isValidCoordinates(center.lat, center.lon) ||
      !isFiniteNumber(area.radius_nm) || area.radius_nm < 1 || area.radius_nm > 150) return false;
  if (!isFiniteNumber(b.lamin) || !isFiniteNumber(b.lamax) ||
      !isFiniteNumber(b.lomin) || !isFiniteNumber(b.lomax) ||
      b.lamin < -90 || b.lamax > 90 || b.lamin > b.lamax ||
      b.lomin < -180 || b.lomin > 180 || b.lomax < -180 || b.lomax > 180) return false;

  const keys = ["flights", "military", "satellites", "cctv"] as const;
  const countKey = { flights: "live_flights", military: "military_flights", satellites: "satellites", cctv: "cctv" } as const;
  for (const key of keys) {
    if (!["online", "degraded", "offline"].includes(String(sources[key]))) return false;
    const entries = layers[key];
    if (!Array.isArray(entries) || entries.length > 100_000) return false;
    for (const item of entries as unknown[]) {
      if (!obj(item) || typeof item.id !== "string" || item.id.length === 0 || item.id.length > 200 ||
          !isFiniteNumber(item.lat) || !isFiniteNumber(item.lon) ||
          !isValidCoordinates(item.lat, item.lon)) return false;
      if (key === "flights" || key === "military") {
        if (item.type !== "flight" || typeof item.icao24 !== "string" ||
            !finiteOrNull(item.altitude_ft) || !finiteOrNull(item.speed_kts) ||
            !finiteOrNull(item.heading_deg) || !finiteOrNull(item.vertical_rate) ||
            !(item.last_seen === null || validTime(item.last_seen))) return false;
        if (key === "military" && item.category !== "military") return false;
      } else if (key === "satellites") {
        if (item.type !== "satellite" || typeof item.name !== "string" ||
            typeof item.norad_id !== "string" ||
            (item.context !== "OVERHEAD" && item.context !== "NEARBY") ||
            !finiteOrNull(item.altitude_km) || !finiteOrNull(item.velocity_kms) ||
            !finiteOrNull(item.azimuth) || !finiteOrNull(item.elevation) ||
            !(item.last_seen === null || validTime(item.last_seen))) return false;
      } else {
        if (item.type !== "cctv" || typeof item.name !== "string" ||
            typeof item.agency !== "string" ||
            !["online", "offline", "unknown"].includes(String(item.status)) ||
            !validTime(item.last_checked) ||
            !["preview_url", "stream_url", "page_url"].every(k => item[k] === null || typeof item[k] === "string")) return false;
      }
    }
    const n = counts[countKey[key]];
    if (n !== null && (!Number.isSafeInteger(n) || (n as number) < 0 || n !== entries.length)) return false;
    if (sources[key] === "offline" && (n !== null || entries.length !== 0)) return false;
  }
  const total = counts.total_assets;
  if (total !== null && (!Number.isSafeInteger(total) || (total as number) < 0)) return false;
  const values = keys.map(key => counts[countKey[key]] as number | null);
  if (values.some(n => n === null)) return total === null;
  return total === values.reduce<number>((sum, n) => sum + (n || 0), 0);
}
