import { allowProviderRequest, cachedProvider, fetchJson } from "./cache";
import { cleanText, distanceNm, isFiniteNumber, type CameraAsset, type Center, type ProviderResult } from "./types";

const CALTRANS_D05 = "https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json";
function safeHttpUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try { const u = new URL(value); return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : null; } catch { return null; }
}
function nested(obj: unknown, ...keys: string[]): unknown {
  let v = obj;
  for (const key of keys) { if (!v || typeof v !== "object") return undefined; v = (v as Record<string, unknown>)[key]; }
  return v;
}
export async function getCameras(center: Center, radiusNm: number): Promise<ProviderResult<CameraAsset>> {
  const key = `caltrans-d05-cctv:${center.lat.toFixed(3)}:${center.lon.toFixed(3)}:${radiusNm}`;
  return cachedProvider(key, 180_000, async () => {
    if (!allowProviderRequest("caltrans-d05-cctv", 4, 60_000)) throw new Error("Caltrans local provider request budget exhausted");
    const raw = await fetchJson(CALTRANS_D05, { headers: { accept: "application/json" } }, 8_000, 1) as { data?: unknown[] };
    if (!Array.isArray(raw.data)) throw new Error("Caltrans District 5 CCTV response has no data array");
    const checked = new Date().toISOString();
    const items: CameraAsset[] = [];
    for (const entry of raw.data) {
      const camera = nested(entry, "cctv") as Record<string, unknown> | undefined;
      if (!camera) continue;
      const loc = nested(entry, "location") as Record<string, unknown> | undefined;
      const lat = Number(loc?.latitude), lon = Number(loc?.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || distanceNm(center, lat, lon) > radiusNm) continue;
      const name = cleanText(loc?.locationName ?? camera.locationName ?? camera.name, 160) || "Caltrans public traffic camera";
      const id = cleanText(camera.index ?? camera.id ?? camera.cctvId, 100) || `${lat.toFixed(5)},${lon.toFixed(5)}`;
      const current = nested(camera, "imageData", "static", "currentImageURL");
      const fallback = nested(camera, "imageData", "static", "imageURL");
      const preview = safeHttpUrl(current ?? fallback);
      const inService = camera.inService;
      const status: CameraAsset["status"] = inService === true || inService === "true" ? "ONLINE" : inService === false || inService === "false" ? "OFFLINE" : "UNKNOWN";
      items.push({ id, type: "cctv", name, agency: "Caltrans District 5", lat, lon, status,
        preview_url: preview, stream_url: safeHttpUrl(camera.streamURL ?? camera.videoURL),
        page_url: safeHttpUrl(camera.url ?? camera.pageURL),
        last_checked: checked });
    }
    return { items, status: "online" };
  });
}
