# Premium route protection deployment checklist

Use this checklist before enabling protected ClearGlass premium pages in production.

## Authentication and route coverage

- Confirm `middleware.ts` protects every sensitive path prefix (`/premium`, `/api/premium`, and `/api/assets/sign`).
- Confirm login redirects preserve `next` and only allow same-origin redirects after identity-provider callback validation.
- Set `PREMIUM_AUTH_SECRET` to a high-entropy value and rotate it through the deployment secret manager.
- Issue `cg_session` as `HttpOnly`, `Secure`, `SameSite=Lax`, with short expiration and server-side revocation for privileged accounts.

## Server-only rendering

- Keep premium copy, workflows, prompts, and operator playbooks in server components, server actions, or protected route handlers.
- Do not import premium content into client components or public static assets.
- Verify production bundles do not contain premium strings with `rg "sensitive phrase" .next/static`.

## Downloadable assets

- Set `ASSET_SIGNING_SECRET` to a high-entropy value distinct from the auth secret.
- Serve files from private object storage or a protected route; never place premium files under `public/`.
- Keep signed URL/token TTLs short and cache headers `private, no-store` unless a stronger storage-layer policy is in place.

## Metadata, accessibility, and copyright

- Keep canonical metadata on protected pages so search engines receive stable URLs without exposing premium content.
- Keep the visible copyright notice in the global shell and on premium templates.
- Validate keyboard navigation, visible focus, form labels, and screen-reader flow; do not add client overlays that trap focus or block inputs.

## Logging and abuse response

- Export structured middleware and route-handler logs to the production SIEM.
- Monitor request fingerprints, referrers, timestamps, unauthorized redirects, asset-token failures, and unusual bursts.
- Alert on burst thresholds, repeated invalid tokens, suspicious referrers, and geographically impossible session use.
