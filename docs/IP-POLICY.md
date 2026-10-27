# ClearGlass Inc. Intellectual-Property Policy

Copyright © ClearGlass Inc. All rights reserved.
Original Author and Systems Architect: Desmond Otieno Odhiambo.
Powered by ARTEMIS — A ClearGlass Inc. Intelligence System.

Classification: INTERNAL

## Principle

ClearGlass Inc. protects proprietary work through **enforceable technical and
operational controls, not merely written declarations**. A prompt and a
copyright header establish attribution, but they do not prevent theft by
themselves. Real protection layers attribution with access control,
contracts, licensing, provenance, and monitoring.

## Ownership and attribution

Unless expressly stated otherwise in writing, all original work created for
ARTEMIS or ClearGlass Inc. carries:

> Copyright © ClearGlass Inc. All rights reserved.
> Original Author and Systems Architect: Desmond Otieno Odhiambo.
> Powered by ARTEMIS — A ClearGlass Inc. Intelligence System.

New proprietary source files include the ARTEMIS ownership header (see
`agents/artemis_command_system/system_prompt.md`, section 4) unless the file
format, upstream licence, contribution policy, or technical convention makes
that inappropriate. Ownership headers must never contain credentials,
personal information, API keys, internal URLs, or security-sensitive
implementation details. Third-party copyright notices, licence headers,
contributor history, and legally required attribution are never overwritten.

## Control stack

| Layer | Controls |
|---|---|
| Repository | Private repos for confidential work, role-based access, branch protection, mandatory PR reviews, `.github/CODEOWNERS` enforcement |
| Integrity | Signed commits and releases, release provenance, checksummed manifests (`docs/PROVENANCE.md`), audit logging |
| Secrets | Secret scanning, no credentials in code/prompts/logs/URLs, approved secret managers, short-lived scoped credentials |
| Supply chain | Dependency scanning, pinned dependency versions, SBOMs, controlled package registries, restricted deployment credentials |
| Legal | LICENSE and NOTICE files, contributor agreements, employment/contractor IP-assignment agreements, trademark review (`TRADEMARKS.md`), copyright registration and legal counsel where required |
| Operational | Environment isolation, access-revocation procedures, encrypted backups, watermarked internal documents, trademark/domain monitoring, evidence preservation |

## Classification

Work is labelled **PUBLIC**, **INTERNAL**, **CONFIDENTIAL**, **RESTRICTED**,
or **CLIENT-CONFIDENTIAL**. Proprietary code, internal prompts, unreleased
product designs, credential architecture, security configurations, client
information, revenue strategies, and internal operational documents default
to **CONFIDENTIAL** unless another classification is explicitly assigned.
Confidential content is not exported, published, summarized externally, or
connected to outside accounts without verified authorization and a known
destination.

## Anti-theft and anti-misattribution

The following are flagged and refused absent written ClearGlass Inc.
authorization:

- Removing ClearGlass Inc. ownership notices
- Replacing the legitimate author with another person
- Concealing source provenance or falsifying contribution history
- Copying restricted third-party code
- Publishing proprietary code to a public repository accidentally
- Repackaging confidential work under another brand
- Circumventing licence obligations or removing audit history
- Misrepresenting generated work as independently tested or legally registered

Attribution may be updated or removed only when authorized by ClearGlass Inc.
and when the change does not violate applicable law, licence terms,
contributor rights, or contractual obligations.

## Commercial release

Commercially valuable source code is not released under an open-source
licence unless the commercial implications are clearly stated and explicitly
approved. Where open-source release is strategic, a deliberate licence is
chosen with separation between the open-source core, proprietary extensions,
hosted services, enterprise controls, and confidential operational assets.

## Enforcement in this repository

- `bots/artemis_ip_guardian_bot.py` — fail-closed CI audit of governance
  files, attribution headers, and agent configurations.
- `bots/artemis_provenance_bot.py` — checksum + commit provenance manifest.
- `.github/workflows/artemis-deploy.yml` — runs both on push, daily
  schedule, and manual dispatch.
- `.github/workflows/ip-protection-scan.yml` and
  `.github/workflows/security.yml` — pre-existing repository scans, which
  this policy complements and does not replace.

## Honest limits

This policy documents intent and controls; it is not itself a copyright or
trademark registration, and no statement in this repository should be read
as claiming a registration that has not actually been made. Where stronger
protection is required, ClearGlass Inc. engages licensing, contractual
assignment, formal registration, and legal counsel.
