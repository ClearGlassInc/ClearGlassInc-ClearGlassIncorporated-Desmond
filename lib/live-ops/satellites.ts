import { cachedProvider, fetchJson } from "./cache";
import { distanceNm, isFiniteNumber, type Center, type ProviderResult, type SatelliteAsset } from "./types";

export async function getSatellites(center: Center, radiusNm: number): Promise<ProviderResult<SatelliteAsset>> {
  const key = `n2yo:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 45_000, async () => {
    const apiKey = process.env.SATELLITE_API_KEY;
    if (!apiKey) throw new Error("SATELLITE_API_KEY is not configured");
    // N2YO's radius is an angular radius from zenith, NOT a ground-distance radius.
    const queryAbove = async (radiusDegrees: number) => {
      const url = `https://api.n2yo.com/rest/v1/satellite/above/${center.lat}/${center.lon}/0/${radiusDegrees}/0/&apiKey=${encodeURIComponent(apiKey)}`;
      const response = await fetchJson(url, { headers: { accept: "application/json" } }, 8_000, 1) as { above?: unknown[] };
      if (!Array.isArray(response.above)) throw new Error("N2YO response has no above array");
      return response.above;
    };
    const normalize = (raw: unknown[], maxDistanceNm: number, context: SatelliteAsset["context"]): SatelliteAsset[] => {
      const items: SatelliteAsset[] = [];
      for (const sat of raw as Record<string, unknown>[]) {
        if (!sat || !isFiniteNumber(sat.satid) || typeof sat.satname !== "string" || !isFiniteNumber(sat.satlat) || !isFiniteNumber(sat.satlng)) continue;
        if (distanceNm(center, sat.satlat, sat.satlng) > maxDistanceNm) continue;
        items.push({
          id: String(sat.satid), type: "satellite", name: sat.satname.slice(0, 120), norad_id: sat.satid,
          lat: sat.satlat, lon: sat.satlng, altitude_km: isFiniteNumber(sat.satalt) ? sat.satalt : null,
          velocity_kms: null, azimuth: null, elevation: null,
          last_seen: new Date().toISOString(), context
        });
      }
      return items;
    };
    // Search a modest cone around zenith, then enforce the actual geographic radius against
    // each satellite's provider-supplied ground footprint.
    const angularRadius = Math.min(90, Math.max(5, radiusNm / 6));
    const overheadRaw = await queryAbove(angularRadius);
    let items = normalize(overheadRaw, radiusNm, "OVERHEAD");
    if (items.length === 0) {
      // Wider sky cone; only label results NEARBY if their actual ground footprint is within
      // an expanded geographic search radius. Do not reinterpret the angular cone as miles.
      const nearbyRaw = await queryAbove(Math.min(90, Math.max(20, angularRadius * 3)));
      items = normalize(nearbyRaw, Math.min(600, radiusNm * 5), "NEARBY");
    }
    return { items, status: "online" };
  });
}
