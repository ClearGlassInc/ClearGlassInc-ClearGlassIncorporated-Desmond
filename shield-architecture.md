# ClearGlass Shield — Architecture & Claims Gate

**Status:** Architecture-stage product definition.  
**Product:** ClearGlass Shield  
**Brand:** ClearGlassInc  
**Tagline:** Privacy you can verify.

## Executive boundary

This repository may describe and prototype ClearGlass Shield, but the product must not be represented as an operating VPN, audited no-logs service, anonymous-access service, or available subscription until the relevant engineering, operational, legal, and independent-assurance gates are complete.

## Core product

ClearGlass Shield is designed as a privacy-first secure-connectivity platform combining:

- encrypted private access;
- minimized identity collection;
- network leak controls;
- verifiable infrastructure and release evidence;
- optional privacy/performance routing modes;
- a separate enterprise security plane with customer-controlled telemetry.

## Claims gate

The following language is prohibited until evidence supports it:

- "untraceable";
- "anonymous";
- "zero logs";
- "no logs" as an unconditional product guarantee;
- "better than Mullvad";
- guarantees against law enforcement identification, browser tracking, malware, fraud detection, or traffic correlation.

The preferred public posture is evidence-qualified language tied to the actual data-flow architecture and independent assurance.

## Private tier data model

The gateway should be architected so that persistent browsing activity, DNS query history, source IP history, destination IP history, connection timestamps, session-duration histories, and per-account traffic histories are not required for normal Private-mode operation.

This is an engineering target, not an audited assertion.

Authentication, payment, support, and gateway operations must remain logically separated.

## Gateway target

- hardened minimal Linux;
- read-only root filesystem;
- immutable signed images;
- memory-resident runtime where practical;
- secure boot target;
- remote-attestation target;
- signed updates;
- configuration-drift detection;
- staged rollout and automatic rollback.

## Client target

Phase-one client scope:

- Windows first;
- WireGuard-first transport;
- kill switch;
- auto-connect;
- tunnel DNS;
- IPv6 protection;
- basic split tunneling;
- automated DNS, IPv6, WebRTC, reconnect, and kill-switch leak tests.

Later platforms:

- macOS;
- Linux;
- Android;
- iOS;
- router support;
- browser extension only after threat-model and platform review.

## ClearGlass Proof

The public trust surface should eventually expose:

1. server inventory;
2. infrastructure ownership/provider model;
3. service health that does not expose user activity;
4. signed client and server release hashes;
5. SBOMs;
6. signing-key fingerprints;
7. independent audit scope and results;
8. remediation status;
9. quarterly privacy transparency reports;
10. aggregate legal-request statistics;
11. security incident history;
12. vulnerability disclosure process;
13. reproducible-build instructions.

## Veil

Veil is an optional traffic-shaping and routing layer. Its documented purpose is to reduce selected observable traffic-pattern signals.

It must not be marketed as defeating every traffic-analysis or endpoint-identification technique.

Validation must specify:

- threat model;
- observable signal;
- baseline;
- control;
- test methodology;
- performance cost;
- known limitations.

## Shield Teams

Teams is intentionally separate from the Private privacy model.

Target controls:

- SAML/OIDC SSO;
- SCIM;
- passkeys;
- TOTP;
- hardware security keys;
- device trust/posture;
- private gateways;
- dedicated egress;
- per-team DNS and access policy;
- customer-controlled SIEM export;
- customer-defined retention;
- administrator audit trail;
- management API;
- Terraform provider;
- incident-response export bundle.

Security-relevant enterprise events are expected and must be documented as part of the Teams data-flow model.

## Build sequence

### Phase 0 — Claims and compliance

- choose operating jurisdiction with specialist advice;
- map all data flows;
- define processing and retention;
- threat model;
- abuse-handling policy;
- legal-request policy;
- vulnerability disclosure policy;
- separate payment/support/auth/gateway systems.

**Gate:** policy-to-system data map complete and reviewed before any no-logs claim.

### Phase 1 — Private beta

- WireGuard-first control plane;
- Windows client;
- Android client;
- core leak controls;
- Access ID;
- 3–5 controlled regions;
- status page;
- initial server inventory;
- automated leak testing.

**Gate:** controlled beta evidence, no unresolved critical leak failures, signed releases.

### Phase 2 — Trust and performance

- immutable gateway images;
- secure boot;
- signing;
- attestation;
- drift controls;
- reproducible client builds;
- ClearGlass Proof;
- controlled port forwarding;
- multi-hop;
- experimental Veil;
- independent audit.

**Gate:** published audit scope/remediation state and gateway-integrity evidence.

### Phase 3 — Teams revenue

- SSO/MFA/SCIM/RBAC;
- dedicated egress;
- SIEM export;
- customer policy controls;
- Terraform provider;
- management API;
- paid onboarding;
- support SLA;
- configurable telemetry retention.

## Commercial status

The proposed prices are targets only:

| Plan | Target |
|---|---:|
| Shield Private | $6/month or $60/year |
| Shield Veil | $10/month or $96/year |
| Shield Teams | $12/user/month |
| Shield Edge | Custom |

Do not activate checkout, subscriptions, billing, or paid-content gating from this specification alone.

## Security and legal review gates

Before public launch, require documented review of:

- privacy/data-protection obligations in operating jurisdictions;
- consumer terms and disclosures;
- abuse handling;
- copyright/DMCA or equivalent legal-request process where applicable;
- sanctions/export-control exposure;
- payment-provider requirements;
- incident notification obligations;
- marketing substantiation;
- independent security assessment;
- infrastructure-provider terms.

## Repository implementation rule

The current website change is intentionally limited to an architecture-stage product page. It does not create a VPN backend, route traffic, collect customer data, activate payments, or assert completed audits.

Production deployment remains a separate approval gate.
