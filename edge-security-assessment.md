# Edge Security Assessment

Status: implementation-ready, provider changes not applied.

## Repository findings

- Public site: static HTML/CSS/JS from the repository root, published by GitHub Pages.
- Public custom hostname: `www.clearglassinc.com` from the root `CNAME` file.
- Pages deployment: `.github/workflows/pages.yml` builds a static artifact with `tools/build_pages.py` and deploys through GitHub Pages.
- Root Node package: build/test tooling, not the public-site runtime.
- Dynamic services also exist in the monorepo, including Next.js admin/storefront applications and API routes. Those services must be protected as separate origins if exposed publicly.
- Existing edge work exists under `clearglass-commerce/infra/cloudflare/`; this implementation follows the repository's Terraform convention and observe-first rollout model.
- Existing `_headers` documents a useful CSP and response-header baseline, but GitHub Pages does not consume Netlify-style `_headers`; those headers are not reliably enforced by Pages itself.
- No evidence was found that the root Pages site is already behind a repository-managed reverse proxy.

## Runtime and integration observations

The public site is static but uses client-side third-party resources. The existing header policy already accounts for the currently known baseline sources:

- scripts: self, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`
- styles/fonts: self, Google Fonts, cdnjs
- images/media: self, data/blob and HTTPS images/media
- network: self, `formspree.io`, `api.github.com`
- frames: `youtube-nocookie.com`
- forms: self and Formspree

Because inline scripts/styles exist, a strict CSP would break the current frontend. The edge rollout therefore starts with CSP Report-Only, preserving the repository's existing source list. Promotion to enforcing CSP requires browser validation and removal/noncing of inline code.

## Authentication, APIs, forms, and webhooks

- The root Pages frontend has no server-side authentication boundary.
- Dynamic subprojects contain authentication/API routes and environment-variable based configuration; they must not be treated as GitHub Pages content.
- Public form handling includes Formspree.
- Future APIs, admin routes and webhooks are represented in the provider-neutral edge policy even if they are not currently routed through the public Pages hostname.

## Secrets and environment handling

This assessment records variable names only. Never commit values.

Existing application subprojects use environment variables. The new edge layer requires the names documented in `infra/edge/README.md` and the GitHub Actions workflow. Provider credentials are only consumed from CI/environment secrets.

## Current limitations

### GitHub Pages origin lockdown

GitHub Pages cannot require a Cloudflare-only shared secret, mTLS client certificate, custom origin header, source-IP ACL, or authenticated origin pull. Therefore a determined client may still reach the GitHub Pages origin through GitHub-controlled hostnames if it knows them. The custom domain can still be proxied through an edge provider, which protects normal public traffic, but this is not equivalent to a private origin.

For strong origin lockdown, migrate the static artifact to an origin that supports authenticated origin access, such as Cloudflare R2/Workers, an object store behind CloudFront, Azure Storage behind Front Door, or a private application/load balancer origin.

### Edge provider administration

DNS, TLS, WAF enablement, Logpush destinations, plan-specific bot features, and provider credentials cannot be applied by this repository alone. Those are documented as manual/operator actions. Terraform is prepared to manage supported resources once credentials and IDs are supplied.

## Risk priorities

1. Put the custom hostname behind a managed edge proxy.
2. Establish logging before enforcement.
3. Add managed WAF and conservative custom rules in observe/challenge-first modes.
4. Enforce response headers at the edge.
5. Protect future API/admin origins separately from GitHub Pages.
6. Move the static origin off GitHub Pages if non-bypassable origin access control becomes a hard requirement.
