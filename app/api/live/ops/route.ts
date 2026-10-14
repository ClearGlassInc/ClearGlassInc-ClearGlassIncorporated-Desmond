import { NextRequest, NextResponse } from "next/server";
import { isIP } from "node:net";
import { allowRequest } from "@/lib/live-ops/cache";
import { getOpenSky } from "@/lib/live-ops/opensky";
import { getMilitaryFlights } from "@/lib/live-ops/adsbexchange";
import { getSatellites } from "@/lib/live-ops/satellites";
import { getCameras } from "@/lib/live-ops/cctv";
import { boundsFor, type LiveOpsResponse, type ProviderResult, type FlightAsset, type SatelliteAsset, type CameraAsset } from "@/lib/live-ops/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const DEFAULT_CENTER = { lat: 36.57, lon: -121.525 };
const DEFAULT_RADIUS_NM = 40;
const MAX_RADIUS_NM = 150;
function clientRateLimitKey(request: NextRequest): string {
  // Reverse proxy must strip client-supplied forwarding headers and append the actual peer IP.
  // Use the last hop, not the leftmost user-controlled X-Forwarded-For value.
  const chain = request.headers.get("x-forwarded-for");
  const candidate = chain?.split(",").map(value => value.trim()).filter(Boolean).at(-1);
  return candidate && isIP(candidate) ? candidate : "unknown";
}
const validNum = (value: string | null, fallback: number) => {
  if (value === null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : NaN;
};
function health<T>(result: ProviderResult<T>): "online" | "degraded" | "offline" { return result.status; }
function jsonError(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers: { "Cache-Control": "no-store" } });
}
export async function GET(request: NextRequest) {
  const clientKey = clientRateLimitKey(request);
  if (!allowRequest(clientKey, 30, 60_000)) return jsonError("Request limit exceeded; retry shortly.", 429);
  const params = request.nextUrl.searchParams;
  const lat = validNum(params.get("lat"), DEFAULT_CENTER.lat);
  const lon = validNum(params.get("lon"), DEFAULT_CENTER.lon);
  const radiusNm = validNum(params.get("radius_nm"), DEFAULT_RADIUS_NM);
  if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180 || !Number.isFinite(radiusNm) || radiusNm < 1 || radiusNm > MAX_RADIUS_NM) {
    return jsonError("Invalid query. lat must be -90..90, lon -180..180, radius_nm 1..150.", 400);
  }
  const center = { lat, lon }, bounds = boundsFor(center, radiusNm);
  const [flightsResult, militaryResult, satellitesResult, cctvResult] = await Promise.allSettled([
    getOpenSky(center, radiusNm, bounds), getMilitaryFlights(center, radiusNm), getSatellites(center, radiusNm), getCameras(center, radiusNm)
  ]);
  const unwrap = <T,>(r: PromiseSettledResult<ProviderResult<T>>): ProviderResult<T> =>
    r.status === "fulfilled" ? r.value : { items: [], status: "offline", error: r.reason instanceof Error ? r.reason.message : "Provider request failed." };
  const fr = unwrap(flightsResult), mr = unwrap(militaryResult), sr = unwrap(satellitesResult), cr = unwrap(cctvResult);
  const militaryIds = new Set(mr.items.map(x => x.icao24.toLowerCase()));
  const flights = (fr.items as FlightAsset[]).filter(x => !militaryIds.has(x.icao24.toLowerCase()));
  const military = mr.items as FlightAsset[];
  const satellites = sr.items as SatelliteAsset[];
  const cctv = cr.items as CameraAsset[];
  const count = (result: ProviderResult<unknown>, items: unknown[]) => result.status === "offline" ? null : items.length;
  const response: LiveOpsResponse = {
    generated_at: new Date().toISOString(),
    area: { center, radius_nm: radiusNm, bounds },
    counts: {
      live_flights: count(fr, flights), military_flights: count(mr, military),
      satellites: count(sr, satellites), cctv: count(cr, cctv),
      total_assets: [count(fr, flights), count(mr, military), count(sr, satellites), count(cr, cctv)].some(x => x === null) ? null : flights.length + military.length + satellites.length + cctv.length
    },
    layers: { flights, military, satellites, cctv },
    sources: { flights: health(fr), military: health(mr), satellites: health(sr), cctv: health(cr) },
    errors: Object.fromEntries(([
      ["flights", fr.error], ["military", mr.error], ["satellites", sr.error], ["cctv", cr.error]
    ] as const).filter((entry): entry is readonly [string, string] => Boolean(entry[1]))) as LiveOpsResponse["errors"]
  };
  return NextResponse.json(response, { headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
}
