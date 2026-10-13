import { cachedProvider, fetchJson } from "./cache";
import { cleanText, distanceNm, isFiniteNumber, type Center, type FlightAsset, type ProviderResult, type Bounds } from "./types";

const M_TO_FT = 3.280839895;
const MS_TO_KTS = 1.943844492;
const MS_TO_FPM = 196.850394;
export async function getOpenSky(center: Center, radiusNm: number, bounds: Bounds): Promise<ProviderResult<FlightAsset>> {
  const key = `opensky:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 7_000, async () => {
    const url = new URL("https://opensky-network.org/api/states/all");
    url.searchParams.set("lamin", String(bounds.lamin)); url.searchParams.set("lomin", String(bounds.lomin));
    url.searchParams.set("lamax", String(bounds.lamax)); url.searchParams.set("lomax", String(bounds.lomax));
    const headers: Record<string, string> = { accept: "application/json" };
    const id = process.env.OPENSKY_CLIENT_ID, secret = process.env.OPENSKY_CLIENT_SECRET;
    if (id && secret) headers.authorization = "Basic " + Buffer.from(`${id}:${secret}`).toString("base64");
    const raw = await fetchJson(url.toString(), { headers }, 7_000, 1) as { states?: unknown[][] | null; time?: number };
    if (!Array.isArray(raw.states)) throw new Error("OpenSky response has no states array");
    const items: FlightAsset[] = [];
    for (const s of raw.states) {
      if (!Array.isArray(s) || typeof s[0] !== "string" || !isFiniteNumber(s[5]) || !isFiniteNumber(s[6])) continue;
      const lat = s[6], lon = s[5];
      if (distanceNm(center, lat, lon) > radiusNm) continue;
      const seen = isFiniteNumber(s[4]) ? s[4] : isFiniteNumber(s[3]) ? s[3] : null;
      items.push({
        id: s[0].toLowerCase(), type: "flight", icao24: s[0].toLowerCase(), lat, lon,
        callsign: cleanText(s[1], 16), country: cleanText(s[2], 80),
        altitude_ft: isFiniteNumber(s[7]) ? Math.round(s[7] * M_TO_FT) : isFiniteNumber(s[13]) ? Math.round(s[13] * M_TO_FT) : null,
        speed_kts: isFiniteNumber(s[9]) ? Math.round(s[9] * MS_TO_KTS) : null,
        heading_deg: isFiniteNumber(s[10]) ? s[10] : null,
        vertical_rate: isFiniteNumber(s[11]) ? Math.round(s[11] * MS_TO_FPM) : null,
        on_ground: typeof s[8] === "boolean" ? s[8] : null,
        squawk: cleanText(s[14], 8), last_seen: seen === null ? null : new Date(seen * 1000).toISOString()
      });
    }
    return { items, status: "online" };
  });
}
