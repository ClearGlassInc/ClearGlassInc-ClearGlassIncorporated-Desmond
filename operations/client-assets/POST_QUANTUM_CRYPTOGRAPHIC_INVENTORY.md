# ClearGlass Post-Quantum Cryptographic Inventory

**Purpose:** Create a defensible inventory of cryptographic assets and dependencies, rank migration exposure, and establish a practical roadmap for crypto-agility and future post-quantum transition.

## Executive rule

Do not begin a broad post-quantum migration until you can identify where cryptography is used, what it protects, who owns it, how long the protected data must remain confidential, and whether each dependency can be changed.

## Engagement objective

Treat post-quantum readiness first as an inventory and dependency-management program. The immediate objective is to reduce uncertainty and create a governed migration sequence before future cryptographic requirements become urgent, contractual, or regulator-driven.

## Discovery scope

### Certificates and PKI

- TLS and mutual-TLS certificates.
- Internal and public certificate authorities.
- Code-signing certificates and signing keys.
- Device, VPN, Wi-Fi, email, identity, document-signing, and application certificates.
- Certificate expiry, issuer, key type, algorithm, key length, owner, system, and renewal process.

### Applications and software

- Custom applications and source-code dependencies.
- Libraries and frameworks implementing TLS, SSH, VPN, signing, encryption, or key exchange.
- Mobile, desktop, browser-extension, embedded, and API software.
- SBOMs where available.
- Vendor commitments on cryptographic upgrades and algorithm support.

### Infrastructure and networks

- VPN gateways, firewalls, routers, load balancers, proxies, wireless controllers, and remote-access platforms.
- Cloud KMS, HSMs, secrets managers, and identity providers.
- Databases, storage, backups, replication, and disaster-recovery platforms.
- OT, industrial systems, cameras, sensors, building systems, and field devices where relevant.

### Data and retention horizon

- Data categories protected by encryption or signatures.
- Confidentiality duration: short-lived, medium-term, long-lived, or permanent.
- Archived data and backups that may remain valuable or sensitive for many years.
- Legal, contractual, regulatory, customer, and intellectual-property obligations.
- Cross-border data and supplier dependencies.

### Governance and recovery

- Crypto policy, standards, architecture records, and exception process.
- Named owners for certificate management, keys, application cryptography, and third-party assurance.
- Ability to rotate keys, change algorithms, update certificates, and replace incompatible devices without disruptive redesign.
- Incident response for exposed keys, broken algorithms, compromised certificates, or vendor end-of-support.

## Inventory record

Maintain one record per cryptographic asset or dependency:

| Field | Required entry |
|---|---|
| Asset identifier | Unique ID or configuration item |
| Business service | Process or service supported |
| System owner | Accountable business and technical owners |
| Environment | Production, test, development, field, or third party |
| Function | Encryption, signing, authentication, key exchange, hashing, or certificate validation |
| Algorithm and parameters | Algorithm, mode, protocol, key type, and key size where available |
| Data classification | Public, internal, confidential, personal, regulated, proprietary, or safety-related |
| Confidentiality horizon | How long protection must remain reliable |
| Dependency type | Internal, cloud, SaaS, OEM, managed service, or open source |
| Change capability | Easy, planned upgrade, contract-dependent, unknown, or end-of-life |
| Evidence source | Scan, configuration export, contract, vendor attestation, interview, or architecture record |
| Risk rating | Impact, urgency, confidence, and recommended action |

## Risk prioritization

Prioritize using four questions:

1. Does the asset protect information that must remain confidential long enough to create future cryptographic exposure?
2. Is the implementation difficult, costly, or slow to replace?
3. Is the system externally exposed, safety-critical, business-critical, or part of a trust chain?
4. Is the organization dependent on a supplier with unclear upgrade commitments?

## 30/60/90-day readiness plan

| Period | Actions | Validation |
|---|---|---|
| First 30 days | Establish owner, scope critical services, collect certificate and network inventory, identify long-lived confidential data, and identify unknowns | Leadership receives coverage map and named owners |
| Days 31–60 | Map application, cloud, vendor, and device dependencies; collect vendor migration commitments; identify crypto-agility gaps | Evidence register and prioritized exposure list are reviewed |
| Days 61–90 | Define target standards, upgrade sequences, procurement requirements, testing plan, and exception process | Approved roadmap, accountable actions, and measurable milestones |

## Procurement requirements

Strategic technology suppliers should be required, on request, to provide:

- Current cryptographic protocols, algorithms, and key-management practices used in the supplied service.
- A documented roadmap for cryptographic agility and post-quantum transition support as standards and customer requirements mature.
- Advance notice of material cryptographic changes and end-of-support dates.
- A supported method to rotate certificates, keys, and trust anchors without unacceptable service interruption.
- Evidence that relevant cryptographic dependencies can be identified within the service.

## Deliverables

1. **Cryptographic inventory workbook** — assets, algorithms, owners, evidence, dependencies, and confidence ratings.
2. **Long-lived data exposure assessment** — systems where delayed transition has the highest business consequence.
3. **Vendor assurance tracker** — supplier algorithm support, migration plans, upgrade dates, and evidence gaps.
4. **Crypto-agility roadmap** — prioritized remediation, renewal, procurement, and architecture actions.
5. **Executive risk brief** — decisions required, residual exposure, and progress metrics.

## Board-level questions

1. Which data must remain confidential long enough to create future cryptographic exposure?
2. Which systems cannot readily change their cryptography because of vendor, device, architecture, or contract constraints?
3. Which suppliers cannot yet show a credible upgrade path?
4. Do we have one accountable inventory for certificates, keys, algorithms, and trust dependencies?
5. What milestones will prove that our highest-risk cryptographic dependencies are becoming easier to change?