import test from "node:test";
import assert from "node:assert/strict";
import { boundsFor, cleanText, distanceNm, inBounds, isLiveOpsResponse, isValidCoordinates, parseFiniteNumber, tileZoomForRadius, webMercatorPixels } from "../lib/live-ops/types";
import { allowProviderRequest, cachedProvider } from "../lib/live-ops/cache";
import { isMilitaryAircraft, normalizeOnGround } from "../lib/live-ops/adsbexchange";
import { getCameras, normalizeCameraStatus, safeHttpUrl } from "../lib/live-ops/cctv";
import type { SatelliteAsset } from "../lib/live-ops/types";

test("Chualar 40 NM bounds contain the center and stay finite", () => {
  const center = { lat: 36.57, lon: -121.525 };
  const bounds = boundsFor(center, 40);
  assert.ok(inBounds(center.lat, center.lon, bounds));
  assert.ok(bounds.lamin < center.lat && bounds.lamax > center.lat);
  assert.ok(bounds.lomin < center.lon && bounds.lomax > center.lon);
  assert.ok(Object.values(bounds).every(Number.isFinite));
});

test("great-circle distance uses nautical miles", () => {
  assert.equal(distanceNm({ lat: 36.57, lon: -121.525 }, 36.57, -121.525), 0);
  assert.ok(distanceNm({ lat: 36.57, lon: -121.525 }, 37.57, -121.525) > 59);
  assert.ok(distanceNm({ lat: 36.57, lon: -121.525 }, 37.57, -121.525) < 61);
});

test("bounds rejects non-finite and outside coordinates", () => {
  const bounds = boundsFor({ lat: 36.57, lon: -121.525 }, 40);
  assert.equal(inBounds(Number.NaN, -121.5, bounds), false);
  assert.equal(inBounds(0, 0, bounds), false);
});

test("external text strips control characters and caps length", () => {
  assert.equal(cleanText("  flight\u0000\n id  "), "flight id");
  assert.equal(cleanText("abcdef", 3), "abc");
  assert.equal(cleanText("  "), null);
});

test("Web Mercator helpers produce finite coordinates for Chualar", () => {
  const p = webMercatorPixels(36.57, -121.525, tileZoomForRadius(36.57, 40));
  assert.ok(Number.isFinite(p.x) && p.x > 0);
  assert.ok(Number.isFinite(p.y) && p.y > 0);
});

test("coordinate sanitizers reject absent and out-of-range values", () => {
  assert.equal(parseFiniteNumber(null), null);
  assert.equal(parseFiniteNumber(""), null);
  assert.equal(parseFiniteNumber("36.57"), 36.57);
  assert.equal(isValidCoordinates(36.57, -121.525), true);
  assert.equal(isValidCoordinates(91, -121.525), false);
  assert.equal(isValidCoordinates(36.57, 181), false);
});

test("ADS-B military classification requires the provider military bit or explicit flag", () => {
  assert.equal(isMilitaryAircraft({ dbFlags: 1 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 3 }), true);
  assert.equal(isMilitaryAircraft({ dbFlags: 2 }), false);
  assert.equal(isMilitaryAircraft({ mil: true }), true);
  assert.equal(isMilitaryAircraft({ flight: "NAVY1" }), false);
});

test("ADS-B on-ground normalization preserves missing values as unknown", () => {
  assert.equal(normalizeOnGround("ground"), true);
  assert.equal(normalizeOnGround(12000), false);
  assert.equal(normalizeOnGround(null), null);
  assert.equal(normalizeOnGround(undefined), null);
});

test("camera status normalization follows the lowercase API contract", () => {
  assert.equal(normalizeCameraStatus(true), "online");
  assert.equal(normalizeCameraStatus("true"), "online");
  assert.equal(normalizeCameraStatus(false), "offline");
  assert.equal(normalizeCameraStatus("false"), "offline");
  assert.equal(normalizeCameraStatus(undefined), "unknown");
  assert.equal(normalizeCameraStatus("yes"), "unknown");
});

test("satellite NORAD identifiers use string values in the normalized schema", () => {
  const satellite: SatelliteAsset = {
    id: "25544", type: "satellite", name: "INTERNATIONAL SPACE STATION", norad_id: "25544",
    lat: 36.57, lon: -121.525, altitude_km: 420, velocity_kms: null,
    azimuth: null, elevation: null, last_seen: null, context: "NEARBY"
  };
  assert.equal(typeof satellite.norad_id, "string");
});

test("provider request budgets are isolated per provider", () => {
  const provider = "test-provider-" + Date.now();
  assert.equal(allowProviderRequest(provider, 1, 60_000), true);
  assert.equal(allowProviderRequest(provider, 1, 60_000), false);
  assert.equal(allowProviderRequest(provider + "-other", 1, 60_000), true);
});


test("provider fetch does not retry permanent client errors", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response("{}", { status: 401, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
  try {
    const { fetchJson } = await import("../lib/live-ops/cache");
    await assert.rejects(fetchJson("https://provider.invalid", {}, 1_000, 2), /HTTP 401/);
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("provider fetch rejects payloads larger than its configured limit", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async () => new Response('{"payload":"this is too large"}', {
    status: 200,
    headers: { "content-type": "application/json" }
  })) as typeof fetch;
  try {
    const { fetchJson } = await import("../lib/live-ops/cache");
    await assert.rejects(fetchJson("https://provider.invalid", {}, 1_000, 0, 8), /size limit/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Web Mercator map projection keeps Chualar centered and chooses bounded zoom", () => {
  for (const radius of [20, 40, 60, 100, 150]) {
    const zoom = tileZoomForRadius(36.57, radius);
    assert.ok(zoom >= 3 && zoom <= 13);
    const center = webMercatorPixels(36.57, -121.525, zoom);
    const samePoint = webMercatorPixels(36.57, -121.525, zoom);
    assert.equal(center.x, samePoint.x);
    assert.equal(center.y, samePoint.y);
  }
});

test("antimeridian radius includes both sides of the dateline", () => {
  const center = { lat: 0, lon: 179.8 };
  const bounds = boundsFor(center, 40);
  assert.ok(bounds.lomin > bounds.lomax);
  assert.equal(inBounds(0, 179.9, bounds), true);
  assert.equal(inBounds(0, -179.9, bounds), true);
  assert.equal(inBounds(0, -177, bounds), false);
  assert.equal(inBounds(0, 175, bounds), false);
});

test("antimeridian on the western side remains wrapped", () => {
  const bounds = boundsFor({ lat: 0, lon: -179.8 }, 40);
  assert.ok(bounds.lomin > bounds.lomax);
  assert.equal(inBounds(0, 179.9, bounds), true);
  assert.equal(inBounds(0, -179.9, bounds), true);
});

test("geospatial bounds reject invalid radii and coordinates", () => {
  assert.throws(() => boundsFor({ lat: 91, lon: 0 }, 40), RangeError);
  assert.throws(() => boundsFor({ lat: 0, lon: 0 }, 0), RangeError);
  assert.throws(() => boundsFor({ lat: 0, lon: 0 }, Number.NaN), RangeError);
});

test("unified response validator rejects malformed or invented count states", () => {
  const good = {
    generated_at: "2026-10-24T20:00:00.000Z",
    area: { center: { lat: 36.57, lon: -121.525 }, radius_nm: 40, bounds: boundsFor({ lat: 36.57, lon: -121.525 }, 40) },
    layers: { flights: [], military: [], satellites: [], cctv: [] },
    sources: { flights: "offline", military: "offline", satellites: "offline", cctv: "offline" },
    counts: { live_flights: null, military_flights: null, satellites: null, cctv: null, total_assets: null },
    errors: {}
  };
  assert.equal(isLiveOpsResponse(good), true);
  assert.equal(isLiveOpsResponse({ ...good, counts: { ...good.counts, satellites: 838.5 } }), false);
  assert.equal(isLiveOpsResponse({ ...good, sources: { ...good.sources, military: "LIVE" } }), false);
  assert.equal(isLiveOpsResponse({ ...good, layers: { ...good.layers, cctv: [{ id: "a", lat: null, lon: 0 }] } }), false);
  assert.equal(isLiveOpsResponse({ ...good, generated_at: "not a timestamp" }), false);
  assert.equal(isLiveOpsResponse({ ...good, area: null }), false);
  assert.equal(isLiveOpsResponse({ ...good, area: { ...good.area, radius_nm: 0 } }), false);
  assert.equal(isLiveOpsResponse({ ...good, layers: { ...good.layers, flights: [{ id: "fake", type: "satellite", lat: 36, lon: -121 }] } }), false);
  assert.equal(isLiveOpsResponse({ ...good, counts: { ...good.counts, total_assets: 99 } }), false);
  assert.equal(isLiveOpsResponse({ ...good, sources: { ...good.sources, cctv: "online" }, counts: { ...good.counts, cctv: 5, total_assets: null } }), false);
});

test("Caltrans camera URLs must resolve to official HTTPS California government hosts", () => {
  assert.equal(safeHttpUrl("https://cwwp2.dot.ca.gov/data/camera.jpg"), "https://cwwp2.dot.ca.gov/data/camera.jpg");
  assert.equal(safeHttpUrl("https://evil.ca.gov.attacker.example/cam"), null);
  assert.equal(safeHttpUrl("http://cwwp2.dot.ca.gov/cam"), null);
  assert.equal(safeHttpUrl("https://example.com/cam"), null);
  assert.equal(safeHttpUrl("https://user:pass@cwwp2.dot.ca.gov/cam"), null);
  assert.equal(safeHttpUrl("javascript:alert(1)"), null);
});

test("expired last-good records are degraded only for a bounded stale window", async () => {
  const savedNow = Date.now;
  let fakeNow = 1_790_000_000_000;
  Date.now = () => fakeNow;
  const cacheKey = "chualar-expiring-provider-20261024";
  try {
    const initial = await cachedProvider(cacheKey, 7_000, async () => ({
      items: [{ id: "provider-record" }], status: "online" as const
    }));
    assert.equal(initial.status, "online");
    fakeNow += 8_000;
    const degraded = await cachedProvider(cacheKey, 7_000, async () => { throw new Error("network unavailable"); });
    assert.equal(degraded.status, "degraded");
    assert.equal(degraded.stale, true);
    assert.equal(degraded.items.length, 1);
    fakeNow += 70_000;
    const offline = await cachedProvider(cacheKey, 7_000, async () => { throw new Error("network unavailable"); });
    assert.equal(offline.status, "offline");
    assert.equal(offline.items.length, 0);
  } finally {
    Date.now = savedNow;
  }
});

test("Caltrans District 5 official nested JSON produces real coordinate-mapped cameras", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async (input: unknown) => {
    calls += 1;
    assert.equal(String(input), "https://cwwp2.dot.ca.gov/data/d5/cctv/cctvStatusD05.json");
    return new Response(JSON.stringify({ data: [
      { cctv: {
        index: "17", inService: "true",
        location: { locationName: "CHUALAR HWY 101", latitude: "36.57", longitude: "-121.525" },
        imageData: { streamingVideoURL: "https://www.dot.ca.gov/public/stream",
          static: { currentImageURL: "https://www.dot.ca.gov/camera/updated.jpg" } }
      } },
      { cctv: {
        index: "18", inService: "false",
        location: { locationName: "MISSING COORDS", latitude: null, longitude: null },
        imageData: {}
      } }
    ] }), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
  try {
    const result = await getCameras({ lat: 36.57, lon: -121.525 }, 40);
    assert.equal(calls, 1);
    assert.equal(result.status, "online");
    assert.equal(result.items.length, 1);
    const camera = result.items[0];
    assert.equal(camera.id, "17");
    assert.equal(camera.lat, 36.57);
    assert.equal(camera.lon, -121.525);
    assert.equal(camera.status, "online");
    assert.equal(camera.preview_url, "https://www.dot.ca.gov/camera/updated.jpg");
    assert.equal(camera.stream_url, "https://www.dot.ca.gov/public/stream");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
