// Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
// Proprietary and confidential. See LICENSE for terms.
/**
 * Image URL normalisation.
 *
 * Stripe stores an image as a URL and fetches it from the public internet, so
 * anything that is not a reachable https URL is worse than no image: it renders
 * as a broken thumbnail on the hosted Checkout page. A filesystem path is the
 * common mistake — `assets/img/cable.png` on a developer's laptop means nothing
 * to Stripe — so relative paths are resolved against the GitHub Pages base URL
 * and anything that looks like a local path is refused outright.
 */

/** Stripe accepts at most eight images per product. */
export const MAX_IMAGES = 8;

export interface ImageResult {
  ok: boolean;
  url?: string;
  reason?: string;
}

/** Windows drive letters and UNC paths — never valid as a Stripe image URL. */
const WINDOWS_PATH = /^(?:[A-Za-z]:[\\/]|\\\\)/;

/**
 * Resolve one source image reference to a public https URL.
 *
 * `baseUrl` is the GitHub Pages origin (plus any project path); relative
 * references are resolved against it the same way a browser would.
 */
export function normalizeImageUrl(raw: unknown, baseUrl: string): ImageResult {
  if (typeof raw !== "string" || raw.trim() === "") {
    return { ok: false, reason: "image reference is empty" };
  }
  const value = raw.trim();

  if (WINDOWS_PATH.test(value)) {
    return { ok: false, reason: `local filesystem path is not a public URL: ${value}` };
  }
  if (/^file:/i.test(value)) {
    return { ok: false, reason: `file: URLs are not reachable by Stripe: ${value}` };
  }
  if (/^data:/i.test(value)) {
    return { ok: false, reason: "data: URIs are not accepted as Stripe product images" };
  }
  if (/^http:\/\//i.test(value)) {
    return { ok: false, reason: `image must be served over https, got ${value}` };
  }
  // Any other explicit scheme (ftp:, s3:, javascript:) is out.
  if (/^[a-z][a-z0-9+.-]*:/i.test(value) && !/^https:\/\//i.test(value)) {
    return { ok: false, reason: `unsupported URL scheme: ${value}` };
  }

  let resolved: URL;
  try {
    resolved = new URL(value, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  } catch {
    return { ok: false, reason: `image reference is not a resolvable URL: ${value}` };
  }
  if (resolved.protocol !== "https:") {
    return { ok: false, reason: `resolved image URL is not https: ${resolved.href}` };
  }
  return { ok: true, url: resolved.href };
}

/**
 * Normalise a product's image list, dropping the ones Stripe could not fetch.
 *
 * Failures are returned rather than thrown: a bad thumbnail should not stop a
 * price from syncing, but it must show up in the report.
 */
export function normalizeImages(
  raws: unknown,
  baseUrl: string,
): { images: string[]; failures: string[] } {
  const list = Array.isArray(raws) ? raws : raws == null ? [] : [raws];
  const images: string[] = [];
  const failures: string[] = [];
  for (const raw of list) {
    const result = normalizeImageUrl(raw, baseUrl);
    if (result.ok && result.url) {
      if (images.length >= MAX_IMAGES) {
        failures.push(`more than ${MAX_IMAGES} images supplied; ${result.url} was dropped`);
        continue;
      }
      if (!images.includes(result.url)) images.push(result.url);
    } else {
      failures.push(result.reason ?? "image could not be normalised");
    }
  }
  return { images, failures };
}

/**
 * Confirm each URL actually serves an image, with a HEAD request.
 *
 * Only run when explicitly asked for (`--check-images`): it is the one part of
 * the tool that touches the network outside Stripe, and a dry run should stay
 * offline by default.
 */
export async function verifyImagesReachable(
  urls: string[],
  timeoutMs = 8000,
): Promise<{ url: string; reason: string }[]> {
  const failures: { url: string; reason: string }[] = [];
  for (const url of urls) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { method: "HEAD", signal: controller.signal });
      if (!response.ok) {
        failures.push({ url, reason: `HEAD returned HTTP ${response.status}` });
        continue;
      }
      const type = response.headers.get("content-type") ?? "";
      if (type && !type.toLowerCase().startsWith("image/")) {
        failures.push({ url, reason: `content-type is ${type}, expected an image/* type` });
      }
    } catch (error) {
      failures.push({ url, reason: (error as Error).message });
    } finally {
      clearTimeout(timer);
    }
  }
  return failures;
}
