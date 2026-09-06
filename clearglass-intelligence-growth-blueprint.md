# ClearGlass Intelligence Growth Blueprint

ClearGlass Intelligence is positioned as a premium briefing hub for governed AI, cyber defense, OSINT, autonomy, operational intelligence, and security playbooks for serious builders.

## Head Implementation

Every HTML page includes browser tab icons, Apple touch icon, Safari pinned tab support, a web manifest, theme color, and Microsoft tile metadata. The canonical public domain remains `https://www.clearglassinc.com/`.

## Favicon Implementation Checklist

- `/icon.svg`
- `/assets/images/clearglass-logo.png` as the reusable Apple touch / fallback icon
- `/safari-pinned-tab.svg`
- `/assets/images/clearglass-logo.png` for Microsoft tile and manifest icons
- `/site.webmanifest`
- existing logo/preview assets only; no new binary files in this PR

## Homepage Copy Direction

- Serious builders need governed intelligence.
- AI without control is liability.
- Security is not a feature. It is infrastructure.
- The future belongs to operators who can govern intelligence.
- ClearGlass exists for builders who need clarity, control, and execution.

## Blog Homepage Layout

1. Featured intelligence brief.
2. Latest intelligence feed.
3. Topic cluster cards for governed AI, cyber defense, OSINT, autonomy, security playbooks, and operational intelligence.
4. Start Here path for new readers.
5. Newsletter or lead-capture CTA.
6. High-trust footer with About, Blog, Systems, Contact, Intelligence Briefs, privacy, and ClearGlass attribution.

## Article Ideas

1. AI Without Governance Is Liability
2. Security Is Infrastructure, Not a Feature
3. OSINT Workflows That Survive Contact With Reality
4. The Founder Cyber Defense Framework
5. How to Govern Agentic Software Before It Governs You
6. Audit Trails for Autonomous AI Systems
7. Operational Intelligence for Serious Builders
8. Crypto Risk Discipline for Technical Founders
9. AI Threat Detection in High-Trust Systems
10. The ClearGlassInc Product Vision for Disciplined Operators

## Reusable Article Outline

- Title: sharp tactical headline.
- Subtitle: one-sentence promise.
- Opening: threat, opportunity, or strategic problem in under 120 words.
- Why it matters: business, security, and operational stakes.
- Framework: three to seven decision points.
- Execution: practical steps and checklists.
- ClearGlass Angle: how ClearGlass thinks about the issue.
- Internal Links: three to five relevant pages.
- CTA: one direct next action.

## Ethical Distribution Pack

For each article, produce five Threads posts, five X posts, three LinkedIn posts, one short email newsletter, three short-form video scripts, five pull quotes, five comment/reply angles, three headline variations, and three CTA variations. Do not automate spam, scrape audiences, fake engagement, or use deceptive claims.

## SEO Metadata Pack

Each page should define a unique title, meta description, canonical URL, Open Graph title, Open Graph description, Open Graph image, Open Graph URL, Twitter card, Twitter title, Twitter description, Twitter image, author metadata, and robots metadata.

## GitHub Pages Deployment Checklist

1. Keep all public asset paths root-relative.
2. Verify `/site.webmanifest` returns valid JSON.
3. Verify favicon assets return `200` from the site root.
4. Validate HTML head metadata on homepage and blog index.
5. Confirm Open Graph image references an existing committed asset such as `/assets/images/clearglass-logo.png`.
6. Run the SEO validator before deployment.
7. Commit generated assets and metadata updates together.
