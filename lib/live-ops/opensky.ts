import { allowProviderRequest, cachedProvider, fetchJson } from "./cache";
import { cleanText, distanceNm, isFiniteNumber, isValidCoordinates, type Center, type FlightAsset, type ProviderResult, type Bounds } from "./types";

const M_TO_FT = 3.280839895;
const MS_TO_KTS = 1.943844492;
const MS_TO_FPM = 196.850394;
let tokenCache: { value: string; expiresAt: number } | null = null;
let tokenRequest: Promise<string> | null = null;

async function openSkyBearerToken(clientId: string, clientSecret: string): Promise<string> {
  if (tokenCache && tokenCache.expiresAt > Date.now() + 60_000) return tokenCache.value;
  if (tokenRequest) return tokenRequest;
  tokenRequest = (async () => {
    const body = new URLSearchParams({ grant_type: "client_credentials", client_id: clientId, client_secret: clientSecret });
    const response = await fetchJson("https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token", {
      method: "POST", headers: { accept: "application/json", "content-type": "application/x-www-form-urlencoded" }, body
    }, 7_000, 1) as { access_token?: unknown; expires_in?: unknown };
    if (typeof response.access_token !== "string" || !response.access_token) throw new Error("OpenSky OAuth response did not contain an access token");
    const expiresIn = isFiniteNumber(response.expires_in) ? Math.max(120, response.expires_in) : 1800;
    tokenCache = { value: response.access_token, expiresAt: Date.now() + expiresIn * 1000 };
    return response.access_token;
  })();
  try { return await tokenRequest; } finally { tokenRequest = null; }
}
export async function getOpenSky(center: Center, radiusNm: number, bounds: Bounds): Promise<ProviderResult<FlightAsset>> {
  const key = `opensky:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 7_000, async () => {
    if (!allowProviderRequest("opensky", 8, 60_000)) throw new Error("OpenSky local provider request budget exhausted");
    const url = new URL("https://opensky-network.org/api/states/all");
    url.searchParams.set("lamin", String(bounds.lamin)); url.searchParams.set("lomin", String(bounds.lomin));
    url.searchParams.set("lamax", String(bounds.lamax)); url.searchParams.set("lomax", String(bounds.lomax));
    url.searchParams.set("extended", "1");
    const headers: Record<string, string> = { accept: "application/json" };
    const id = process.env.OPENSKY_CLIENT_ID, secret = process.env.OPENSKY_CLIENT_SECRET;
    if (id && secret) headers.authorization = `Bearer ${await openSkyBearerToken(id, secret)}`;
    const raw = await fetchJson(url.toString(), { headers }, 7_000, 1) as { states?: unknown[][] | null; time?: number };
    // OpenSky legitimately returns states: null when the bounding box has no aircraft.
    if (raw.states === null && isFiniteNumber(raw.time)) return { items: [], status: "online" };
    if (!Array.isArray(raw.states)) throw new Error("OpenSky response has no states array");
    const items: FlightAsset[] = [];
    for (const s of raw.states) {
      if (!Array.isArray(s) || typeof s[0] !== "string" || !/^[a-fA-F0-9]{6}$/.test(s[0]) || !isFiniteNumber(s[5]) || !isFiniteNumber(s[6])) continue;
      const lat = s[6], lon = s[5];
      if (!isValidCoordinates(lat, lon)) continue;
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
        squawk: cleanText(s[14], 8), category: isFiniteNumber(s[17]) ? s[17] : null, last_seen: seen === null ? null : new Date(seen * 1000).toISOString()
      });
    }
    return { items, status: "online" };
  });
}
