import type { ProviderResult } from "./types";

type Entry<T> = { expiresAt: number; value: ProviderResult<T> };
const cache = new Map<string, Entry<unknown>>();
const inflight = new Map<string, Promise<ProviderResult<unknown>>>();
const limits = new Map<string, { started: number; count: number }>();

export async function cachedProvider<T>(key: string, ttlMs: number, loader: () => Promise<ProviderResult<T>>): Promise<ProviderResult<T>> {
  const now = Date.now();
  const entry = cache.get(key) as Entry<T> | undefined;
  if (entry && entry.expiresAt > now) return entry.value;
  const active = inflight.get(key) as Promise<ProviderResult<T>> | undefined;
  if (active) return active;
  const task = (async () => {
    try {
      const fresh = await loader();
      if (fresh.status !== "offline") cache.set(key, { expiresAt: Date.now() + ttlMs, value: fresh });
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

/** Best-effort per-process guard. Use a shared store (e.g. Redis) for multi-instance deployments. */
export function allowRequest(key: string, maxRequests = 30, windowMs = 60_000): boolean {
  const now = Date.now();
  const bucket = limits.get(key);
  if (!bucket || now - bucket.started >= windowMs) {
    limits.set(key, { started: now, count: 1 });
    return true;
  }
  if (bucket.count >= maxRequests) return false;
  bucket.count += 1;
  return true;
}
export async function fetchJson(url: string, init: RequestInit = {}, timeoutMs = 8_000, retries = 1): Promise<unknown> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { ...init, signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error(`Provider returned HTTP ${response.status}`);
      const type = response.headers.get("content-type") || "";
      if (!type.toLowerCase().includes("json")) throw new Error("Provider returned a non-JSON response");
      return await response.json();
    } catch (error) {
      lastError = error;
      if (attempt < retries) await new Promise(resolve => setTimeout(resolve, 250 * (attempt + 1)));
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Provider request failed");
}
