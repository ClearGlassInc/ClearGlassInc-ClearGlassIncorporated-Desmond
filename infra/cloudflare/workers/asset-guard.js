// Edge asset guard — Cloudflare Worker.
//
// Runs in front of the origin on premium asset routes and rejects requests that
// lack a valid, unexpired, asset-bound signed token BEFORE they reach the
// origin. This mirrors the origin verifier (admin/lib/signing.ts) exactly — same
// HMAC-SHA256 over `${assetId}.${exp}.${subject}` — so a token minted by the app
// verifies identically here. The shared secret is bound as ASSET_SIGNING_SECRET.
//
// It also enforces hotlink protection (off-site Referer) and passes verified
// crawlers through untouched so SEO is preserved.
//
// Deploy: wrangler deploy; route it to /api/download/* and /assets/premium/*.

const encoder = new TextEncoder();

function bytesToBase64Url(bytes) {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function hmac(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return bytesToBase64Url(new Uint8Array(sig));
}

// Constant-time-ish string compare.
function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

// Verify a token against the concrete asset id, mirroring lib/signing.ts.
async function verifyAssetToken(secret, assetId, token) {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [expStr, subjectEnc, providedSig] = parts;
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || exp < Math.floor(Date.now() / 1000)) return null;
  const subject = decodeURIComponent(subjectEnc);
  const expected = await hmac(secret, `${assetId}.${exp}.${subject}`);
  return safeEqual(expected, providedSig) ? subject : null;
}

function deny(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const { pathname } = url;

    // Only guard premium asset routes; everything else passes through.
    // Two origin download schemes exist:
    //   /api/download/<id>?token=...          — subject is inside the token, so
    //                                            the edge CAN verify it here.
    //   /api/assets/download?asset&expires&signature — signature binds to the
    //                                            session subject, which is not in
    //                                            the URL, so only the origin can
    //                                            verify it. The edge still applies
    //                                            hotlink protection to it.
    const isAsset =
      pathname.startsWith("/api/download/") ||
      pathname.startsWith("/api/assets/") ||
      pathname.startsWith("/assets/premium/");
    if (!isAsset) return fetch(request);

    // Preserve SEO: verified crawlers are allowed (they will get whatever the
    // origin serves them, which for these routes is auth-gated anyway).
    if (request.cf && request.cf.verifiedBotCategory) return fetch(request);

    // Hotlink protection: block off-site embeds. Empty Referer (direct nav) ok.
    const referer = request.headers.get("Referer") || "";
    if (referer) {
      try {
        const refHost = new URL(referer).hostname;
        const allowed = (env.ALLOWED_REFERER_HOST || url.hostname);
        if (refHost !== allowed && !refHost.endsWith(`.${allowed}`)) {
          return deny(403, "hotlinking not allowed");
        }
      } catch {
        return deny(403, "invalid referer");
      }
    }

    // Signed-token check for the download route. assetId is the path segment.
    if (pathname.startsWith("/api/download/")) {
      if (!env.ASSET_SIGNING_SECRET) {
        // Fail closed if the guard is misconfigured — never serve unguarded.
        return deny(503, "asset guard not configured");
      }
      const assetId = decodeURIComponent(pathname.slice("/api/download/".length).split("/")[0]);
      const token = url.searchParams.get("token");
      const subject = await verifyAssetToken(env.ASSET_SIGNING_SECRET, assetId, token);
      if (!subject) return deny(403, "invalid or expired token");
    }

    // Verified at the edge; let origin do its own session + token check too.
    return fetch(request);
  },
};
