import { allowProviderRequest, cachedProvider, fetchJson } from "./cache";
import { cleanText, distanceNm, isFiniteNumber, isValidCoordinates, type Center, type FlightAsset, type ProviderResult } from "./types";

/** ADS-B Exchange v2 encodes military status in bit 0 of dbFlags. */
export function normalizeOnGround(value: unknown): boolean | null {
  if (value === "ground") return true;
  if (typeof value === "number" && Number.isFinite(value)) return false;
  if (value === null || value === undefined) return null;
  return null;
}

export function isMilitaryAircraft(value: Record<string, unknown>): boolean {
  const flags = value.dbFlags;
  if (typeof flags === "number" && Number.isFinite(flags)) return (Math.trunc(flags) & 1) === 1;
  if (typeof flags === "string" && /^\d+$/.test(flags)) return (Number.parseInt(flags, 10) & 1) === 1;
  // Some provider responses may also include an explicit boolean.
  return value.mil === true;
}

export async function getMilitaryFlights(center: Center, radiusNm: number): Promise<ProviderResult<FlightAsset>> {
  const key = `adsbx-mil:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 7_000, async () => {
    const apiKey = process.env.ADSBX_API_KEY;
    if (!apiKey) throw new Error("ADSBX_API_KEY is not configured");
    if (!allowProviderRequest("adsbexchange", 10, 60_000)) throw new Error("ADS-B Exchange local provider request budget exhausted");
    // ADS-B Exchange's current v2 API uses the gateway host, /api/aircraft/v2 path,
    // api-auth header, and an "ac" array in the response.
    const url = `https://gateway.adsbexchange.com/api/aircraft/v2/lat/${center.lat}/lon/${center.lon}/dist/${radiusNm}`;
    const raw = await fetchJson(url, {
      headers: { accept: "application/json", "accept-encoding": "gzip", "api-auth": apiKey }
    }, 7_000, 1) as { ac?: unknown[]; msg?: unknown };
    if (!Array.isArray(raw.ac)) throw new Error("ADS-B Exchange v2 response has no ac array");
    const now = Date.now();
    const items: FlightAsset[] = [];
    for (const item of raw.ac) {
      if (!item || typeof item !== "object") continue;
      const a = item as Record<string, unknown>;
      if (!isMilitaryAircraft(a) || typeof a.hex !== "string" || !/^[a-fA-F0-9]{6,8}$/.test(a.hex) || !isFiniteNumber(a.lat) || !isFiniteNumber(a.lon)) continue;
      if (!isValidCoordinates(a.lat, a.lon) || distanceNm(center, a.lat, a.lon) > radiusNm) continue;
      // External age fields can be negative or enormous. Invalid timestamps must not crash a provider batch.
      const ageSeconds = isFiniteNumber(a.seen_pos) && a.seen_pos >= 0 && a.seen_pos <= 31_536_000
        ? a.seen_pos : null;
      const seen = ageSeconds === null ? null : new Date(now - ageSeconds * 1000).toISOString();
      const altitude = isFiniteNumber(a.alt_baro) ? a.alt_baro : isFiniteNumber(a.alt_geom) ? a.alt_geom : null;
      items.push({
        id: a.hex.toLowerCase(), type: "flight", category: "military", icao24: a.hex.toLowerCase(),
        lat: a.lat, lon: a.lon, callsign: cleanText(a.flight, 16), country: cleanText(a.country, 80), operator: cleanText(a.ownOp, 80),
        altitude_ft: altitude, speed_kts: isFiniteNumber(a.gs) ? Math.round(a.gs) : null,
        heading_deg: isFiniteNumber(a.track) ? a.track : null,
        vertical_rate: isFiniteNumber(a.baro_rate) ? a.baro_rate : isFiniteNumber(a.geom_rate) ? a.geom_rate : null,
        on_ground: normalizeOnGround(a.alt_baro), squawk: cleanText(a.squawk, 8), last_seen: seen
      });
    }
    return { items, status: "online" };
  });
}
