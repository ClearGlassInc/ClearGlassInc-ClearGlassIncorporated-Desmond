import type { ProviderResult } from "./types";

type Entry<T> = { expiresAt: number; value: ProviderResult<T> };
const MAX_CACHE_ENTRIES = 512;
const cache = new Map<string, Entry<unknown>>();
const inflight = new Map<string, Promise<ProviderResult<unknown>>>();
const limits = new Map<string, { started: number; count: number }>();
let inboundLimitCalls = 0;
const providerLimits = new Map<string, { started: number; count: number }>();
let providerLimitCalls = 0;

export async function cachedProvider<T>(key: string, ttlMs: number, loader: () => Promise<ProviderResult<T>>): Promise<ProviderResult<T>> {
  const now = Date.now();
  const entry = cache.get(key) as Entry<T> | undefined;
  if (entry && entry.expiresAt > now) return entry.value;
  const active = inflight.get(key) as Promise<ProviderResult<T>> | undefined;
  if (active) return active;
  const task = (async () => {
    try {
      const fresh = await loader();
      if (fresh.status !== "offline") {
        if (!cache.has(key) && cache.size >= MAX_CACHE_ENTRIES) {
          const oldestKey = cache.keys().next().value;
          if (oldestKey !== undefined) cache.delete(oldestKey);
        }
        cache.set(key, { expiresAt: Date.now() + ttlMs, value: fresh });
      }
      else if (entry) return { ...entry.value, status: "degraded" as const, stale: true, error: fresh.error || "Provider unavailable; serving cached data." };
      return fresh;
    } catch (error) {
      if (entry) return { ...entry.value, status: "degraded" as const, stale: true, error: error instanceof Error ? error.message : "Provider failed." };
      return { items: [], status: "offline" as const, error: error instanceof Error ? error.message : "Provider failed." };
    } finally {
      inflight.delete(key);
    }
  })();
  inflight.set(key, task as Promise<ProviderResult<unknown>>);
  return task;
}

/** Best-effort per-process provider request budgets; shared infrastructure is required across instances. */
export function allowProviderRequest(provider: string, maxRequests: number, windowMs: number): boolean {
  const now = Date.now();
  if (++providerLimitCalls % 100 === 0) {
    for (const [key, bucket] of providerLimits) {
      if (now - bucket.started >= windowMs * 2) providerLimits.delete(key);
    }
  }
  const bucket = providerLimits.get(provider);
  if (!bucket || now - bucket.started >= windowMs) {
    providerLimits.set(provider, { started: now, count: 1 });
    return true;
  }
  if (bucket.count >= maxRequests) return false;
  bucket.count += 1;
  return true;
}

/** Best-effort per-process guard. Use a shared store (e.g. Redis) for multi-instance deployments. */
export function allowRequest(key: string, maxRequests = 30, windowMs = 60_000): boolean {
  const now = Date.now();
  if (++inboundLimitCalls % 100 === 0) {
    for (const [limitKey, entry] of limits) {
      if (now - entry.started >= windowMs * 2) limits.delete(limitKey);
    }
  }
  const bucket = limits.get(key);
  if (!bucket || now - bucket.started >= windowMs) {
    limits.set(key, { started: now, count: 1 });
    return true;
  }
  if (bucket.count >= maxRequests) return false;
  bucket.count += 1;
  return true;
}
class ProviderHttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryable: boolean,
    readonly retryAfterMs = 0
  ) {
    super(message);
    this.name = "ProviderHttpError";
  }
}

export async function fetchJson(
  url: string,
  init: RequestInit = {},
  timeoutMs = 8_000,
  retries = 1,
  maxBytes = 5_000_000
): Promise<unknown> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { ...init, signal: controller.signal, cache: "no-store" });
      if (!response.ok) {
        const retryable = response.status === 429 || response.status >= 500;
        const retryAfter = Number(response.headers.get("retry-after"));
        const retryAfterMs = Number.isFinite(retryAfter) && retryAfter > 0
          ? Math.min(5_000, retryAfter * 1000)
          : 0;
        throw new ProviderHttpError(
          "Provider returned HTTP " + response.status,
          response.status,
          retryable,
          retryAfterMs
        );
      }
      const type = response.headers.get("content-type") || "";
      if (!type.toLowerCase().includes("json")) {
        throw new ProviderHttpError("Provider returned a non-JSON response", response.status, false);
      }
      const declaredLength = Number(response.headers.get("content-length"));
      if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
        await response.body?.cancel();
        throw new ProviderHttpError("Provider response exceeded the size limit", response.status, false);
      }
      if (!response.body) throw new Error("Provider response body was empty");
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let totalBytes = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        totalBytes += value.byteLength;
        if (totalBytes > maxBytes) {
          await reader.cancel();
          throw new ProviderHttpError("Provider response exceeded the size limit", response.status, false);
        }
        chunks.push(value);
      }
      const bytes = new Uint8Array(totalBytes);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
      try {
        return JSON.parse(new TextDecoder().decode(bytes)) as unknown;
      } catch {
        throw new ProviderHttpError("Provider returned invalid JSON", response.status, false);
      }
    } catch (error) {
      lastError = error;
      const nonRetryable = error instanceof ProviderHttpError && !error.retryable;
      const canRetry = attempt < retries && !nonRetryable;
      if (!canRetry) break;
      const retryAfterMs = error instanceof ProviderHttpError ? error.retryAfterMs : 0;
      await new Promise(resolve => setTimeout(resolve, retryAfterMs || 250 * (attempt + 1)));
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Provider request failed");
}
