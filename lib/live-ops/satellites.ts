import { cachedProvider, fetchJson } from "./cache";
import { isFiniteNumber, type Center, type ProviderResult, type SatelliteAsset } from "./types";

export async function getSatellites(center: Center, radiusNm: number): Promise<ProviderResult<SatelliteAsset>> {
  const key = `n2yo:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 45_000, async () => {
    const apiKey = process.env.SATELLITE_API_KEY;
    if (!apiKey) throw new Error("SATELLITE_API_KEY is not configured");
    // N2YO's /above endpoint uses an angular search radius in degrees (not nautical miles).
    const angularRadius = Math.min(90, Math.max(0.1, radiusNm / 60));
    const url = `https://api.n2yo.com/rest/v1/satellite/above/${center.lat}/${center.lon}/0/${angularRadius}/0/&apiKey=${encodeURIComponent(apiKey)}`;
    const raw = await fetchJson(url, { headers: { accept: "application/json" } }, 8_000, 1) as { above?: unknown[]; info?: { satcount?: number } };
    if (!Array.isArray(raw.above)) throw new Error("N2YO response has no above array");
    const items: SatelliteAsset[] = [];
    for (const sat of raw.above as Record<string, unknown>[]) {
      if (!sat || !isFiniteNumber(sat.satid) || typeof sat.satname !== "string" || !isFiniteNumber(sat.satlat) || !isFiniteNumber(sat.satlng)) continue;
      const altitude = isFiniteNumber(sat.satalt) ? sat.satalt : null;
      items.push({
        id: String(sat.satid), type: "satellite", name: sat.satname.slice(0, 120), norad_id: sat.satid,
        lat: sat.satlat, lon: sat.satlng, altitude_km: altitude,
        velocity_kms: null, azimuth: null, elevation: null,
        last_seen: new Date().toISOString(), context: "OVERHEAD"
      });
    }
    return { items, status: "online" };
  });
}
