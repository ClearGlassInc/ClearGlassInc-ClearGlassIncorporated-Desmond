export type SourceHealth = "online" | "degraded" | "offline";
export type AssetType = "flight" | "satellite" | "cctv";

export interface Bounds {
  lamin: number; lomin: number; lamax: number; lomax: number;
}
export interface Center { lat: number; lon: number; }
export interface FlightAsset {
  id: string; type: "flight"; lat: number; lon: number;
  altitude_ft: number | null; speed_kts: number | null; heading_deg: number | null;
  callsign: string | null; icao24: string; country: string | null; squawk: string | null;
  on_ground: boolean | null; vertical_rate: number | null; last_seen: string | null;
  category?: "military" | number | null;
}
export interface SatelliteAsset {
  id: string; type: "satellite"; name: string; norad_id: number; lat: number; lon: number;
  altitude_km: number | null; velocity_kms: number | null; azimuth: number | null;
  elevation: number | null; last_seen: string | null; context: "OVERHEAD" | "NEARBY";
}
export interface CameraAsset {
  id: string; type: "cctv"; name: string; agency: string; lat: number; lon: number;
  status: "ONLINE" | "OFFLINE" | "UNKNOWN"; preview_url: string | null;
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
export function cleanText(value: unknown, max = 120): string | null {
  if (typeof value !== "string") return null;
  const text = value.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, max);
  return text || null;
}
export function inBounds(lat: number, lon: number, b: Bounds): boolean {
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= b.lamin && lat <= b.lamax && lon >= b.lomin && lon <= b.lomax;
}
export function distanceNm(a: Center, lat: number, lon: number): number {
  const rad = (n: number) => n * Math.PI / 180;
  const dLat = rad(lat - a.lat), dLon = rad(lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(lat)) * Math.sin(dLon / 2) ** 2;
  return 3440.065 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}
export function boundsFor(center: Center, radiusNm: number): Bounds {
  const dLat = radiusNm / 60;
  const dLon = radiusNm / (60 * Math.max(0.1, Math.cos(center.lat * Math.PI / 180)));
  return { lamin: Math.max(-90, center.lat - dLat), lomin: Math.max(-180, center.lon - dLon), lamax: Math.min(90, center.lat + dLat), lomax: Math.min(180, center.lon + dLon) };
}
