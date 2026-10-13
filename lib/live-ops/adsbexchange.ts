import { cachedProvider, fetchJson } from "./cache";
import { cleanText, distanceNm, isFiniteNumber, type Center, type FlightAsset, type ProviderResult } from "./types";

export async function getMilitaryFlights(center: Center, radiusNm: number): Promise<ProviderResult<FlightAsset>> {
  const key = `adsbx-mil:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 7_000, async () => {
    const apiKey = process.env.ADSBX_API_KEY;
    if (!apiKey) throw new Error("ADSBX_API_KEY is not configured");
    const url = `https://api.adsbexchange.com/v2/lat/${center.lat}/lon/${center.lon}/dist/${radiusNm}/`;
    const raw = await fetchJson(url, { headers: { accept: "application/json", "api-auth": apiKey } }, 7_000, 1) as { aircraft?: unknown[] };
    if (!Array.isArray(raw.aircraft)) throw new Error("ADS-B Exchange response has no aircraft array");
    const now = Date.now();
    const items: FlightAsset[] = [];
    for (const a of raw.aircraft as Record<string, unknown>[]) {
      if (!a || typeof a !== "object" || a.mil !== true || typeof a.hex !== "string" || !isFiniteNumber(a.lat) || !isFiniteNumber(a.lon)) continue;
      if (distanceNm(center, a.lat, a.lon) > radiusNm) continue;
      const seen = isFiniteNumber(a.seen_pos) ? new Date(now - a.seen_pos * 1000).toISOString() : null;
      const altitude = isFiniteNumber(a.alt_baro) ? a.alt_baro : isFiniteNumber(a.alt_geom) ? a.alt_geom : null;
      items.push({
        id: a.hex.toLowerCase(), type: "flight", category: "military", icao24: a.hex.toLowerCase(),
        lat: a.lat, lon: a.lon, callsign: cleanText(a.flight, 16), country: cleanText(a.ownOp, 80),
        altitude_ft: altitude, speed_kts: isFiniteNumber(a.gs) ? Math.round(a.gs) : null,
        heading_deg: isFiniteNumber(a.track) ? a.track : null,
        vertical_rate: isFiniteNumber(a.baro_rate) ? a.baro_rate : isFiniteNumber(a.geom_rate) ? a.geom_rate : null,
        on_ground: a.alt_baro === "ground", squawk: cleanText(a.squawk, 8), last_seen: seen
      });
    }
    return { items, status: "online" };
  });
}
