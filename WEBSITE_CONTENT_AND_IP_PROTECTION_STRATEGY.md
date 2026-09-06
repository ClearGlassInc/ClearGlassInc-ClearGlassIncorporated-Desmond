# ClearGlassInc Artemis website content and IP protection strategy

**Owner:** ClearGlass Inc.  
**Jurisdictional baseline:** Ontario, Canada  
**Status:** implementation playbook; legal review required before relying on any enforcement language  
**Core assumption:** a browser must deliver public content to a visitor, so no client-side control can prevent a determined person from photographing, recording, or reconstructing it. The objective is deterrence, attribution, access control, evidence, and fast response—not impossible “screenshot prevention.”

## 1. Control model and immediate priorities

| Priority | Action | Outcome | Verification |
|---|---|---|---|
| P0 | Keep proprietary playbooks, prompts, datasets, and actionable system details outside public HTML | Disclosure is minimized at the actual trust boundary | Anonymous requests cannot retrieve protected objects or signed URLs after expiry |
| P0 | Preserve the Git history, originals, design sources, contracts, and dated release manifests | Ownership and chronology can be demonstrated | Quarterly evidence-export drill |
| P0 | Publish the Terms of Use and Content Policy, and place a readable copyright notice beside premium content | Visitors receive consistent notice | Link and metadata audit |
| P1 | Apply branded, non-obstructive watermarks to valuable previews and exported artifacts | Captures remain attributable | Responsive, print, and contrast review |
| P1 | Monitor distinctive phrases, visual assets, domains, and marketplaces | Copies are found earlier | Monthly monitoring log |
| P2 | Use opt-in copy friction only on genuinely valuable blocks | Casual copying is less convenient without degrading the whole site | Keyboard, screen-reader, form, mobile, and reduced-motion tests |

Do **not** claim that a notice, watermark, disabled context menu, copyright registration, or trademark registration prevents copying. Do not impair accessibility, clipboard use in forms, browser navigation, security tools, or legitimate quotation. Never collect invasive browser fingerprints as a substitute for evidence.

## 2. Legal and signalling layer

### Public notices

Use the legal entity consistently: **ClearGlass Inc.** Use **ClearGlassInc Artemis** as the product/platform name, followed by `™` only where the company is asserting an unregistered mark and counsel has cleared the usage. Use `®` only after registration for the relevant goods or services.

Recommended adjacent notice:

```html
<p class="ip-notice">
  ClearGlassInc Artemis™ — © 2026 ClearGlass Inc. All rights reserved.
  Concepts, diagrams, workflows, copy, and visual assets may not be reproduced,
  redistributed, or adapted without prior written permission.
  <a href="/legal/terms.html">Terms of Use</a>
</p>
```

The existing [Terms of Use](../legal/terms.html) and [Content Policy](../legal/content-policy.html) should remain the canonical website terms. Before a commercial launch, Ontario/Canadian counsel should confirm assent mechanics, limitation language, licensing, governing law, privacy implications, contractor assignments, and whether a clickwrap agreement is required for gated material.

### Canadian registration recommendations

1. **Copyright:** copyright generally arises automatically when an original work is created, but register high-value releases with the Canadian Intellectual Property Office (CIPO) when the evidentiary and enforcement benefit justifies it. Archive the deposited version, source files, authorship/assignment documents, Git commit, and registration record together. See [CIPO copyright guidance](https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en/copyright).
2. **Trademarks:** commission clearance searches, define the actual goods/services, and seek registration for core names and logos that function as source identifiers. Maintain usage specimens and renewal deadlines. See [CIPO trademarks guidance](https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en/trademarks).
3. **Industrial designs:** ask counsel whether novel visual features of a finished article qualify; website concepts alone should not be assumed registrable. File before disclosure where timing rules matter. See [CIPO industrial-design guidance](https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en/industrial-designs).
4. **Patents and trade secrets:** an abstract idea is not protected merely because it is documented. Discuss patentability *before* public disclosure when there is a novel technical invention. Keep non-public know-how secret through classification, least privilege, NDAs, confidentiality clauses, offboarding, and access logs.
5. **Ownership:** obtain written IP assignment and confidentiality terms from employees, contractors, photographers, designers, and AI/data vendors. Record third-party licences and open-source obligations in the IP register.

This is an operational baseline, not legal advice or a conclusion that any specific asset is registrable or non-infringing.

## 3. Premium visual and interaction design

Apply the shared `/asset-protection.js` to public pages, then opt in only the relevant regions:

```html
<script defer src="/asset-protection.js"></script>

<figure data-cg-watermark="ClearGlassInc Artemis™ · Authorized Preview">
  <img src="/assets/artemis-concept.webp"
       alt="ClearGlassInc Artemis governed intelligence workflow"
       width="1600" height="900" draggable="false">
</figure>

<section data-cg-protected
         data-cg-watermark="© 2026 ClearGlass Inc. · Preview">
  <!-- A short public summary, never the proprietary implementation. -->
</section>
```

The script adds an inert neon/glass watermark and prevents selection/context menus only inside `data-cg-protected`. Inputs, textareas, selects, and editable regions remain selectable. This is friction, not authorization. Keep substantive authorization server-side.

For class-based layouts, the same shared script also supports the requested
anti-copy helpers without changing existing `data-cg-*` integrations:

```html
<section class="protected protected-watermark">
  <h2>Autonomous Agent Framework</h2>
  <p>Reserved codenames, system logic, and architecture are protected.</p>
</section>

<article class="protected blur-preview" tabindex="0">
  Preview becomes readable on hover or keyboard focus.
</article>
```

The `.protected` helper deters selection, context menus, protected copy/save/print
shortcuts, and dragging while retaining selection and shortcut behavior in form
and editable controls. `.protected-watermark` adds the ClearGlassInc confidential
overlay and diagonal capture pattern. `.blur-preview` is optional, supports
keyboard focus, and disables its transition when reduced motion is requested.
The script also emits a random, non-identifying per-page token in
`data-session-watermark` and `<meta name="session-watermark">`; it must not be
treated as authentication, authorization, or proof of visitor identity.

For exported diagrams and PDFs, render the mark into the artifact itself rather than relying on a CSS overlay. Use a non-secret release ID and asset digest so a capture can be matched to the publication register; do not expose a customer email or personal identifier in a public watermark.

Make premium pages valuable because they are live: progressive entity graphs, time-window controls, source lineage, confidence changes, and governed approval states. Static captures should remain intelligible but naturally omit live data and interactions. Avoid fake telemetry, fake urgency, or animations that conceal required information. Respect `prefers-reduced-motion` and preserve a complete keyboard path.

## 4. Technical friction and protected delivery

### Hotlink controls

Prefer an origin/CDN rule that permits same-site requests and direct navigation while denying obvious cross-site embedding. Test search previews, social cards, feeds, and accessibility tools before enforcement. A representative Nginx rule is:

```nginx
location ~* \.(?:avif|gif|jpe?g|png|svg|webp)$ {
    valid_referers none blocked server_names *.clearglassinc.com;
    if ($invalid_referer) { return 403; }
    add_header Cache-Control "public, max-age=86400" always;
}
```

Do not treat `Referer` as authentication—it can be absent or forged. Configure the equivalent managed WAF/CDN rule in audit mode first, inspect false positives, then enforce with a rollback switch.

### Gated content API (Python)

Critical artifacts belong behind authenticated, authorized delivery with short-lived, resource-scoped URLs. The application must deny by default and log metadata without logging tokens:

```python
from datetime import timedelta
from fastapi import Depends, FastAPI, HTTPException, status

app = FastAPI()

@app.post("/v1/assets/{asset_id}/download")
def create_download(asset_id: str, principal=Depends(require_principal)) -> dict[str, str]:
    asset = repository.get_asset(asset_id)
    if asset is None or not policy.can_read(principal, asset):
        # Identical response avoids confirming whether a protected object exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    audit.append("asset.download_granted", actor=principal.id, resource=asset_id)
    return {
        "url": object_store.sign_get(
            key=asset.storage_key,
            expires_in=timedelta(minutes=5),
            response_content_disposition=f'attachment; filename="{asset.safe_filename}"',
        )
    }
```

Production requirements: validate opaque asset identifiers; enforce tenant, compartment, purpose, and export policy at the service; cap response size/rate; revoke sessions; keep buckets private; bind signatures to one object and method; use five-minute or shorter TTLs; never cache protected responses publicly; and retain append-only grant/download events. For novel concepts, publish only outcome, proof, and a bounded preview. Put replicable workflows, prompts, thresholds, source mappings, and implementation detail in an NDA-backed data room.

## 5. IP and provenance register

Maintain an access-controlled register, with immutable history, containing:

```text
asset_id, canonical_title, asset_type, authors, owner, creation_time,
first_publication_time, source_commit, source_digest_sha256, release_digest_sha256,
canonical_url, source_file_locations, licence, third_party_inputs,
assignment_record, confidentiality_class, permitted_disclosures,
copyright_registration, trademark_application, renewal_deadline,
watermark_release_id, monitoring_queries, enforcement_status
```

Hashing shows that a retained file matches a recorded file; it does not independently prove authorship. Timestamped repository history, source materials, assignments, publication records, and registrations supply the broader evidence. Restrict the register because it may contain confidential agreements and personal information.

## 6. Monitoring cadence

| Cadence | Check | Evidence retained |
|---|---|---|
| Continuous | Brand/domain alerts, CDN hotlink/referrer anomalies, abnormal authenticated download rates | Alert ID, query/rule version, timestamps, relevant privacy-minimized logs |
| Weekly | Search distinctive 8–12-word phrases and product names | Search URL, result URL, captured page/PDF, analyst decision |
| Monthly | Copyscape/plagiarism scan and reverse-image searches on flagship visuals | Tool, scan date, match score, source asset ID, analyst decision |
| Quarterly | Marketplace, app-store, code-host, domain, and trademark-watch review | Findings, owner, disposition, deadlines |
| Per release | Archive source and rendered artifacts; compute SHA-256; update register | Commit, build/release ID, digest, canonical URL, approver |

Monitoring vendors receive data; approve them through privacy, security, retention, residency, and contractual review before uploading unpublished or customer material. Google Alerts and public reverse-image tools should receive only already-public content.

## 7. Evidence and takedown playbook

1. **Triage safely.** Record who reported the match, the original asset ID, suspected URL/account, discovery time in UTC, scope, audience, commercial impact, and whether credentials or customer data are exposed. Do not access accounts or systems without authorization.
2. **Preserve evidence.** Capture full-page screenshots with the browser address and clock, save the page/PDF where lawful, record HTTP headers and public registration/hosting facts, calculate SHA-256 digests, and preserve originals read-only. A staff member records collection steps. For consequential disputes, engage counsel or a qualified evidence provider.
3. **Compare.** Create a side-by-side map of protectable expression, branding, dates, access evidence, and licences. Separate copied expression or marks from general ideas, facts, functional patterns, and independently created similarities.
4. **Assess ownership and risk.** Confirm assignments, registrations, third-party rights, fair-dealing/licence questions, jurisdiction, contractual restrictions, and counterclaim risk with counsel. Never send an automated legal threat.
5. **Contact proportionately.** Start with a factual permission/removal request where appropriate: identify the work and canonical URL, describe the specific use, state the requested remedy and reasonable deadline, preserve all correspondence, and avoid unsupported allegations.
6. **Escalate with approval.** Counsel may recommend a cease-and-desist, platform/host copyright or trademark process, search de-indexing request, registrar notice, contractual remedy, or litigation. Use each provider’s current official process; DMCA is a US statutory process and is not a universal shorthand for every jurisdiction.
7. **Track and close.** Log notices, attestations, delivery evidence, responses, counter-notices, deadlines, removals, repeat appearances, cost, and final disposition. Require human approval before every external notice or public statement.
8. **Learn without overreaching.** Update watermark placement, disclosure boundaries, monitoring queries, or contract language. Do not retaliate, dox, launch traffic, evade access controls, or make public accusations without counsel-approved evidence.

### Initial factual notice template (counsel review required)

```text
Subject: Request to review unauthorized use of ClearGlass Inc. material

We are writing regarding [specific URL], observed on [UTC date/time]. ClearGlass
Inc. publishes the identified material at [canonical URL], with records dating to
[date]. The following elements appear reproduced: [precise list].

We have not located permission for this use. Please preserve relevant records and,
by [reasonable date], confirm the basis for use or remove the identified material.
If you believe this notice is mistaken or you hold a licence, reply with the
relevant information. Nothing in this message waives any rights or remedies.

[Authorized contact and case ID]
```

## 8. Rollout and rollback

1. Inventory and classify content: public, public-preview, confidential, or restricted.
2. Move confidential/restricted detail out of static Pages before adding cosmetic controls.
3. Apply notices and `data-cg-watermark` to two flagship preview sections; verify desktop/mobile, print, zoom, keyboard, screen reader, focus, contrast, and reduced motion.
4. Apply `data-cg-protected` only after product and accessibility review. Remove the attribute immediately if it blocks legitimate use; server-side access control remains effective.
5. Put CDN hotlink rules in log-only mode, establish a false-positive baseline, then enforce. Roll back the rule—not the evidence logs—if legitimate previews break.
6. Launch the IP register and monitoring calendar with named legal and security owners.
7. Run a tabletop clone-response exercise. Success means the team can find ownership evidence, calculate artifact hashes, identify the proper platform process, draft a factual notice, and stop at the human approval gate.

## 9. Acceptance criteria

- Every flagship and gated surface has canonical ownership metadata and a visible, readable notice.
- Public HTML contains no restricted implementation detail, secrets, or private object URLs.
- Protected downloads deny unauthorized and cross-compartment access without revealing object existence.
- Watermarks remain visible at mobile, desktop, and print sizes but never obscure content or intercept input.
- Forms and editable regions remain selectable; all controls remain keyboard accessible; reduced-motion preferences are honored.
- Evidence collection and every external enforcement action have a named human owner and append-only case history.
- The IP register links each priority asset to source, owner/assignment, digest, release, monitoring query, and response status.
