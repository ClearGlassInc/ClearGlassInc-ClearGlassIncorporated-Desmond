# Route protection deployment checklist

- Set `ADMIN_LOGIN_TOKEN`, `ADMIN_SESSION_SECRET`, `REQUEST_FINGERPRINT_SECRET`, and `ASSET_SIGNING_SECRET` from the runtime secret manager; never commit production values.
- Keep protected pages and APIs in `middleware.ts` `PROTECTED_PREFIXES`; add every premium route before deployment.
- Confirm premium copy, prompts, and workflows render in server components or protected API routes only; do not place premium payloads in client components, static JSON, or public assets.
- Serve downloadable premium files through short-lived signed URLs or object-store pre-signed URLs; deny direct public bucket access.
- Forward structured security logs to the production SIEM or OpenTelemetry collector and alert on `severity=warn`, denied login spikes, and unusual burst counts.
- Verify canonical metadata, Open Graph metadata, and the visible copyright footer remain present after route changes.
- Run keyboard-only and screen-reader smoke checks on login and protected pages; do not add overlays, disabled form traps, or client-only content blockers.
- In production, verify unauthorized requests to `/`, `/approvals`, `/audit`, `/premium`, `/api/premium/briefing`, and `/api/assets/sign` redirect or deny before any sensitive payload is returned.
- Roll back by reverting the deployment in Apollo/hosting control plane and invalidating active session and asset-signing secrets if exposure is suspected.
