// Signed URLs for downloadable premium assets.
//
// Premium files (playbooks, prompt packs, export bundles) are never served from
// a public/static path. Instead a short-lived, signed token authorises a single
// asset for a bounded window. The download route (app/api/download/[asset]) only
// streams bytes when the token verifies — so a leaked link stops working after
// it expires, and the token cannot be edited to point at a different asset
// (the asset id is inside the signed payload).
//
// Same Web-Crypto-only constraint as auth.ts: runs on Edge and Node.

const encoder = new TextEncoder();

// Default validity for a download link. Long enough for a click, short enough
// that a link pasted into a log or chat is useless within minutes.
export const DEFAULT_ASSET_TTL_SECONDS = 5 * 60;

function getSecret(): string {
  // Separate secret from session signing so rotating one does not invalidate the
  // other. Falls back to AUTH_SECRET, then an insecure dev-only default that
  // production must override (same pattern as auth.ts — never a real credential).
  return (
    process.env.ASSET_SIGNING_SECRET ||
    process.env.AUTH_SECRET ||
    "clearglass-dev-only-insecure-asset-secret"
  );
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function hmacKey(): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(getSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
}

async function sign(message: string): Promise<string> {
  const sig = await crypto.subtle.sign("HMAC", await hmacKey(), encoder.encode(message));
  return bytesToBase64Url(new Uint8Array(sig));
}

export interface SignedAsset {
  /** Opaque token to append as `?token=` on the download URL. */
  token: string;
  /** Absolute expiry (unix seconds) for display / cache decisions. */
  expiresAt: number;
}

/**
 * Produce a signed token binding `assetId` + `subject` to an expiry. The token
 * is `exp.sub.sig` where sig = HMAC(assetId + exp + subject). Because assetId is
 * part of the signed message but NOT the token body, the verifier re-derives the
 * signature from the requested asset — a token minted for asset A cannot be
 * replayed against asset B.
 */
export async function signAsset(
  assetId: string,
  subject: string,
  ttlSeconds: number = DEFAULT_ASSET_TTL_SECONDS,
): Promise<SignedAsset> {
  const exp = Math.floor(Date.now() / 1000) + ttlSeconds;
  const sig = await sign(`${assetId}.${exp}.${subject}`);
  return { token: `${exp}.${encodeURIComponent(subject)}.${sig}`, expiresAt: exp };
}

/**
 * Verify a download token against the concrete `assetId` being requested.
 * Returns the subject (who the link was minted for) when valid, else null.
 */
export async function verifyAssetToken(assetId: string, token: string | null): Promise<string | null> {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [expStr, subjectEnc, providedSig] = parts;
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || exp < Math.floor(Date.now() / 1000)) return null;
  const subject = decodeURIComponent(subjectEnc);
  const expectedSig = await sign(`${assetId}.${exp}.${subject}`);
  if (expectedSig.length !== providedSig.length) return null;
  let mismatch = 0;
  for (let i = 0; i < expectedSig.length; i++) {
    mismatch |= expectedSig.charCodeAt(i) ^ providedSig.charCodeAt(i);
  }
  return mismatch === 0 ? subject : null;
}
