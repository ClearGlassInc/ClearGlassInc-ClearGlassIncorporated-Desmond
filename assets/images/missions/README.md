# Mission Control images

Place mission photography and approved artwork in this folder. Do not use copyrighted imagery unless ClearGlass Inc. has permission to publish it.

## Expected filenames

The sample mission data currently references:

- `artemis-vi.jpg`
- `guardian.jpg`
- `aegis-glass.jpg`
- `fly-deploy.jpg`
- `growth-ops.jpg`
- `cyber-ai-risk.jpg`

For each JPG, you may optionally add same-name optimized formats. The gallery automatically prefers them when the browser supports them:

- `artemis-vi.avif`
- `artemis-vi.webp`
- `artemis-vi.jpg`

Repeat that AVIF/WebP/JPG pattern for each mission image.

## Recommended dimensions

- Source/master: 1800 × 1200 px or larger, 3:2 ratio.
- JPG fallback: 1400–1800 px wide, quality around 78–84.
- WebP: 1400–1800 px wide, quality around 72–82.
- AVIF: 1400–1800 px wide, quality around 45–60 depending on encoder.
- Keep important subjects near the center because mission cards use `object-fit: cover`.

## Adding or replacing a mission

Edit `assets/js/missions.js` and update the mission object's `image`, `alt`, `objective`, `technologies`, and `impact` values. Use a meaningful alt description that explains what the image shows rather than repeating the mission title.

Missing assets are handled gracefully: Mission Control shows a subtle local-image fallback panel instead of a broken-image icon.
