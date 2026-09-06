## What & why
<!-- A concise summary of the change and the motivation. -->

## Changes
<!-- Bullet the key changes. Prefer small, reversible diffs. -->
-

## Type
- [ ] Content / page
- [ ] Design system (`tokens.css` / `buttons.css` / `theme.css` / `ui.css` / `control-surface.js`)
- [ ] Bots / Python (`bots/`, `sentinel/`, `apps/`)
- [ ] CI / workflows
- [ ] Docs

## Checklist
- [ ] Reuses the shared design tokens — no new visual language introduced
- [ ] Accessible: semantic HTML, visible focus, AA contrast, reduced-motion respected
- [ ] No secrets in client-side code
- [ ] New indexable pages added to `sitemap.xml` (or marked exempt in `bots/site_health_bot.py`)
- [ ] `python -m pytest tests/ -q` passes locally
- [ ] CI is green

## Rollback
<!-- How to revert if this misbehaves in production. For Pages, reverting the
     squash-merge commit on `main` redeploys the previous state. -->
Revert the squash-merge commit on `main`; GitHub Pages redeploys automatically.
