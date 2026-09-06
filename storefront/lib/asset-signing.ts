import { createHmac, timingSafeEqual } from "node:crypto";

const TOKEN_VERSION = "v1";
const DEFAULT_TTL_SECONDS = 5 * 60;

function signingSecret(): string {
  const secret = process.env.ASSET_SIGNING_SECRET;
  if (!secret && process.env.NODE_ENV === "production") {
    throw new Error("ASSET_SIGNING_SECRET must be set in production");
  }
  return secret || "dev-only-asset-signing-secret-change-me";
}

function signature(payload: string): string {
  return createHmac("sha256", signingSecret()).update(payload).digest("base64url");
}

export function createAssetToken(assetId: string, subject: string, ttlSeconds = DEFAULT_TTL_SECONDS): string {
  const exp = Math.floor(Date.now() / 1000) + ttlSeconds;
  const payload = Buffer.from(JSON.stringify({ v: TOKEN_VERSION, assetId, sub: subject, exp })).toString("base64url");
  return `${payload}.${signature(payload)}`;
}

export function verifyAssetToken(token: string): { assetId: string; subject: string } | null {
  const [payload, suppliedSignature] = token.split(".");
  if (!payload || !suppliedSignature) return null;
  const expected = signature(payload);
  const supplied = Buffer.from(suppliedSignature);
  const expectedBuffer = Buffer.from(expected);
  if (supplied.length !== expectedBuffer.length || !timingSafeEqual(supplied, expectedBuffer)) return null;

  try {
    const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as {
      v: string;
      assetId: string;
      sub: string;
      exp: number;
    };
    if (parsed.v !== TOKEN_VERSION || !parsed.assetId || !parsed.sub || parsed.exp < Math.floor(Date.now() / 1000)) {
      return null;
    }
    return { assetId: parsed.assetId, subject: parsed.sub };
  } catch {
    return null;
  }
}
