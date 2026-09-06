#!/usr/bin/env python3
"""ClearGlass internal-linking generator.

Injects a compact, self-styled "Continue exploring" block into every indexable
static page, turning the site into a deliberate pillar-and-cluster link network:

  - every page carries a breadcrumb to Home and to its topic pillar
  - every page links to a rotated window of cluster siblings, so inbound link
    equity is distributed across the whole cluster instead of pooling on the
    first few pages
  - curated cross-cluster links (EXTRA_LINKS) bridge related topics
  - every page ends with a two-link CTA path chosen per cluster

The block is static HTML (crawlable without JS execution), delimited by
`cg-related` marker comments, and regenerated in place — safe to re-run any
time the map below changes:

    python3 tools/internal_links.py          # rewrite blocks on all pages
    python3 tools/internal_links.py --check  # exit 1 if any page is stale

stdlib only. The site graph lives in PAGES / CLUSTERS / EXTRA_LINKS below;
to add a page, give it a title + description in PAGES and append it to a
cluster's members.
"""
from __future__ import annotations

import html
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "SITE_WIRING_PLAN.md"

START = "<!-- cg-related:start -->"
END = "<!-- cg-related:end -->"

# HTML utilities and private/non-indexable operational surfaces are deliberately
# outside the public journey graph. Keeping this inventory beside PAGES makes
# the site-wide audit exhaustive without leaking private consoles into search or
# adding conversion UI to redirects, loaders, and transactional completion pages.
# path -> (journey role, reason it must not receive the generated module)
EXCLUDED_PAGES: dict[str, tuple[str, str]] = {
    "404.html": ("Error recovery", "noindex redirect and route-recovery page"),
    "cg-loader.html": ("Application utility", "noindex branded loading surface"),
    "google23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM.html": (
        "Site verification", "Google ownership verification artifact"
    ),
    "header-mockup-2040.html": ("Design prototype", "noindex, nofollow header study"),
    "loader.html": ("Application utility", "noindex branded loading surface"),
    "offers/thank-you.html": ("Conversion completion", "noindex form-success destination"),
    "offline.html": ("Error recovery", "noindex service-worker fallback"),
    "platform-command-center.html": ("Private operations", "noindex command surface"),
    "sentinel/ARTEMIS_FAWL_COMMAND_SURFACE.html": (
        "Private operations", "noindex, nofollow governance console"
    ),
    "sentinel/PHOENIX_DASHBOARD.html": (
        "Private operations", "noindex, nofollow recovery console"
    ),
    "seo-dashboard.html": ("Private operations", "noindex, nofollow SEO console"),
    "threads.html": ("Campaign review", "noindex, nofollow draft review surface"),
}

# --------------------------------------------------------------------------
# Site graph: every indexable page, with descriptive anchor text.
# path -> (short title, description used to build the anchor)
# --------------------------------------------------------------------------
PAGES: dict[str, tuple[str, str]] = {
    # Company / hub
    "index.html": ("ClearGlass Inc.", "governed intelligent systems — home"),
    "investors/index.html": ("Investor Data Room", "corporate documents and diligence materials"),
    "operations/client-onboarding.html": ("Client Onboarding", "how engagements start at ClearGlass"),
    "operations/hubspot-handoff.html": ("HubSpot Handoff", "CRM connection runbook"),
    "operations/ontario-incorporation-handoff.html": ("Ontario Incorporation Handoff", "corporate filing runbook"),
    "operations/stripe-handoff.html": ("Stripe Handoff", "payments connection runbook"),
    "authority-network.html": ("Authority Network", "the ClearGlass pillar-and-cluster site graph"),
    "advanced-features-tools-systems.html": ("Advanced Features, Tools & Systems", "the governed systems, agent and audit architecture catalog"),
    "business-productivity-suite.html": ("Business Productivity Suite", "Canadian-first business productivity planning"),
    "global-growth-engine.html": ("Global Growth Engine", "governed multi-market growth intelligence"),
    "automap.html": ("AutoMap Orchestration", "architecture-aware orchestration and system relationship mapping"),
    "apps/command-center/index.html": ("Growth Command Centre", "governed Burlington growth operations and approvals"),

    # Cyber defense & security operations
    "cyber-defense-console.html": ("Cyber Defense Console", "the ClearGlass command center for defensive operations"),
    "sentinel.html": ("SENTINEL", "live geospatial security command center"),
    "guardian.html": ("GUARDIAN", "intelligence command interface"),
    "bluedesk.html": ("BLUEDESK", "CISO risk and blue-team console"),
    "bluedesk-mobile.html": ("BLUEDESK Mobile", "the CISO risk console on a phone-first canvas"),
    "artemis-blue-team.html": ("Artemis Blue Team", "OSINT-driven defense command center"),
    "stegoforge.html": ("STEGOFORGE", "steganography and covert-channel analysis terminal"),
    "attack-prompt-core.html": ("ATT&CK Prompt Integrator", "MITRE ATT&CK-aligned analysis prompts"),
    "environmental-cyber-risk.html": ("Environmental Cyber-Risk", "OT and environmental threat monitoring"),

    # Intelligence & OSINT
    "intelligence.html": ("Intelligence", "the ClearGlass intelligence practice"),
    "flowsint.html": ("Flowsint", "OSINT investigation graph for domains, IPs and transforms"),
    "Ontario-osint.html": ("Ontario OSINT Deck", "regional open-source intelligence control deck"),
    "clearglass.html": ("Network Flow Intelligence", "see network traffic as living structure"),
    "clearglass-nexus.html": ("ClearGlass NEXUS", "full-spectrum intelligence platform"),
    "ClearGlass-NEXUS-v12-FINAL.html": ("NEXUS v12", "the flagship intelligence platform build"),
    "artemis.html": ("NEXUS v12 · Ontario", "intelligence platform deployment profile"),
    "intelligence-command-surface.html": ("Intelligence Command Surface", "one unified operational picture"),
    "intelligence-interface.html": ("Intelligence Interface 2027", "next-generation analyst workspace"),
    "intelligence-platform.html": ("Intelligence Platform Architecture", "brand and platform blueprint"),
    "docs/guardian_command_nexus_spec.html": ("Guardian Command Nexus Spec", "the implementation specification for the Guardian command surface"),
    "xenolith.html": ("XENOLITH", "the sovereign intelligence lattice — governed multi-domain command substrate"),

    # Artemis platform
    "artemis-os.html": ("Artemis OS", "the Artemis intelligence operating system"),
    "artemis-iv.html": ("ARTEMIS IV", "tactical intelligence core"),
    "artemis-2040.html": ("Artemis 2040", "long-horizon intelligence platform"),
    "artemis-ai-cyber-intelligence-platform.html": ("AI Cyber Intelligence Platform", "Artemis applied to cyber intelligence"),
    "artemis-self-evolving-platform.html": ("Self-Evolving Platform", "Artemis's autonomous improvement loop"),
    "artemis-fawl/index.html": ("ARTEMIS // FAWL", "the governed, self-healing Artemis command platform"),
    "air-control.html": ("ZEPHYR", "air systems control surface"),
    "air-systems-control.html": ("Air Systems Control", "the Artemis airspace control surface"),

    # Command & autonomous operations
    "percival-os.html": ("PERCIVAL OS", "mission-ready governed command center"),
    "artemis-percival.html": ("AVALON", "the ARTEMIS ⊕ PERCIVAL unified fusion core"),
    "agentmesh.html": ("Agent Mesh", "multi-agent OSINT orchestration"),
    "ai-operator.html": ("AI Operator Workspace", "human-in-the-loop agent operations"),
    "command-console.html": ("Command Console", "cyber intelligence operations hub"),
    "conduit.html": ("CONDUIT", "self-hosted open-source workflow automation"),
    "postloop.html": ("PostLoop", "autonomous multi-account content engine"),
    "saas-platform.html": ("Event Control Surface", "event-driven platform operations"),
    "CG-os.html": ("CG OS", "the ClearGlass command HUD"),
    "systems.html": ("Systems Console", "PERCIVAL operations console"),
    "control-surface.html": ("Systems Control Surface v3.1", "the live command dashboard"),
    "command-center.html": ("Command Center", "executive security operations deck"),
    "percival-build.html": ("PERCIVAL BUILD", "spatial engineering workspace"),
    "clearsight.html": ("CLEARSIGHT", "edge-AI camera vision & object detection"),

    # Legal, tax & compliance
    "legal/index.html": ("Legal Infrastructure", "the ClearGlass corporate legal stack"),
    "aegis.html": ("AEGIS", "legal process shield"),
    "corporate-legal-advisor.html": ("ClearCounsel", "corporate legal AI at senior-partner depth"),
    "banking-law-advisor.html": ("ClearBank Legal AI", "banking law and regulatory intelligence"),
    "tax.html": ("ClearTax AI", "U.S. and Canadian tax intelligence"),
    "procurement-legal-tech.html": ("Procurement & Legal-Tech Surface", "public-sector procurement intelligence"),
    "legal/privacy.html": ("Privacy Policy", "how ClearGlass handles data"),
    "legal/terms.html": ("Terms of Service", "the terms governing ClearGlass services"),
    "legal/ai-liability.html": ("AI Liability Framework", "how ClearGlass governs AI risk"),
    "legal/legal-council.html": ("AI Legal Council Framework", "structured multi-advisor legal review"),
    "legal/articles.html": ("Articles of Incorporation", "ClearGlass founding articles"),
    "legal/bylaws.html": ("Corporate Bylaws", "how the corporation is governed"),
    "legal/nda.html": ("Founder NDA & Non-Compete", "confidentiality framework"),
    "legal/ip-assignment.html": ("IP Assignment Agreement", "how IP is assigned to the company"),
    "legal/directors-resolution.html": ("Directors' Resolution", "initial board resolutions"),
    "legal/banking-resolution.html": ("Banking Resolution", "officer and banking authority"),
    "legal/share-subscription.html": ("Share Subscription Agreement", "founder share issuance"),
    "legal/content-policy.html": ("Content Policy", "authorized use, attribution, and copyright ownership"),
    "legal/accessibility.html": ("Accessibility Statement", "our WCAG 2.2 AA commitment and how to report a barrier"),

    # Healthcare
    "clearpulse.html": ("ClearPulse", "healthcare intelligence pipeline"),
    "clearpulse-architecture.html": ("ClearPulse Architecture", "the forensic-AI whitepaper"),
    "offers/phipa-readiness.html": ("PHIPA Readiness", "free checklist and assessment for Ontario health data"),
    "offers/phipa-readiness-checklist.html": ("PHIPA Readiness Checklist", "the printable compliance checklist"),

    # Government & procurement
    "government.html": ("Government Solutions", "federal and public-sector systems"),
    "operations/procurement-readiness.html": ("Procurement Readiness", "verified supplier-registration status"),
    "operations/federal-supplier-handoff.html": ("Federal Supplier Handoff", "supplier registration runbook"),
    "counter-uas-commercialization-os.html": ("Counter-UAS OS", "counter-drone commercialization platform"),
    "traffic-enforcement.html": ("Speed Vision AI", "AI traffic-enforcement platform"),
    "sats-digital-twin.html": ("SATS Digital Twin", "storm-adaptive transit simulation with governed operations"),

    # Services & conversion
    "products.html": ("ClearGlass Products", "the unified ClearGlass product catalog"),
    "offers/index.html": ("Services & Engagements", "every ClearGlass offer in one place"),
    "store.html": ("ClearGlass Store", "book a security engagement"),
    "seo-authority-hub.html": ("Cybersecurity & AI Automation in Burlington", "the local authority hub for ClearGlass services"),
    "checkout/index.html": ("Secure Checkout", "purchase an audit or protection plan"),
    "pricing.html": ("Pricing & Engagements", "plans and engagement models"),
    "plans.html": ("Guardian Plans & Pricing", "per-seat subscription tiers for the Guardian console"),
    "workspace.html": ("ClearGlass Workspace", "business email, storage and collaboration plans per person"),
    "smb-cyber-trust-kit.html": ("SMB Cyber Trust Kit", "plain-language cyber resilience for small business"),
    "smb.html": ("SMB Suite", "intelligent systems for small business"),
    "side-store.html": ("Side Store", "electronics, cables and components"),
    "offers/hardening-sprint.html": ("Hardening Sprint", "Microsoft 365 + Windows hardening engagement"),
    "offers/security-quick-audit.html": ("Security Quick-Audit", "a focused $249 security review"),
    "offers/guardian-command-nexus-blueprint.html": ("Guardian Command Nexus Blueprint", "the full SPEC-1 architecture blueprint, sold as a digital deliverable"),
    "offers/autonomous-threat-modeling.html": ("Autonomous Threat Modeling", "continuous threat-modeling assessment and implementation services"),
    "revenue-engine.html": ("Revenue Engine", "AI-driven business growth system"),

    # Design & UI engineering
    "web-design.html": ("Web Design & Development", "growth infrastructure built by ClearGlass"),
    "ultra-glass.html": ("Ultra Glass", "governed intelligence, rendered visible"),
    "clearglass-ultra.html": ("ClearGlass Ultra", "see through everything"),
    "futuristic.html": ("Aurora Glass", "futuristic control-surface design study"),
    "button-lab.html": ("Button Lab", "machined-glass control components"),
    "button-system.html": ("Button System", "the ClearGlass glass-UI component set"),
    "hover-menu.html": ("Hover Menu", "elegant navigation component study"),

    # Opal-Koboi product assets
    "opal/index.html": ("Opal-Koboi", "advanced automation assets"),
    "products/opal-koboi/index.html": ("Opal-Koboi Assets", "the product asset library"),
    "products/opal-koboi/artemis-iv-core.html": ("Artemis IV Core · Asset", "product sheet"),
    "products/opal-koboi/artemis-vi.html": ("Artemis VI · Asset", "product sheet"),
    "products/opal-koboi/guardian.html": ("Guardian · Asset", "product sheet"),
    "products/opal-koboi/revenue-engine.html": ("Revenue Engine · Asset", "product sheet"),
    "products/opal-koboi/smb-suite.html": ("SMB Suite · Asset", "product sheet"),

    # Insights / blog
    "blog/index.html": ("ClearGlass Intelligence", "essays on governed AI, cyber defense and OSINT"),
    "blog/autonomous-threat-modeling-2026.html": ("Autonomous Threat Modeling in 2026", "continuous architecture-grounded security for agentic and cyber-physical systems"),
    "blog/ai-agent-governance-governed-autonomy.html": ("AI Agent Governance", "the governed-autonomy playbook"),
    "blog/ai-agents-insider-threat.html": ("AI Agents Are the New Insider Threat", "why agent identity is a security boundary"),
    "blog/almach-scalp-engine.html": ("ALMACH Scalp Engine", "a directional neural-mesh trading study"),
    "blog/artemis-governed-ai-gtm-visual-growth-engine.html": ("Governed AI Threat Modeling", "the Artemis GTM visual growth engine"),
    "blog/clearglass-agentops-microsoft-foundry-future-stack.html": ("ClearGlass AgentOps", "the Microsoft Foundry future stack"),
    "blog/clearglass-command-center-cyber-defense-console.html": ("Inside the Command Center", "designing a cyber defense console"),
    "blog/clearglass-platform-audit-2026.html": ("The ClearGlass Platform Audit", "keep, simplify, gate, build — the platform upgrade doctrine"),
    "blog/clearglass-secure-deployment-agent.html": ("The Secure Deployment Agent", "governed authorization for every production push"),
    "blog/clearglassinc-0-to-1m-corporate-execution-plan.html": ("$0-to-$1M Execution Plan", "the corporate build-out playbook"),
    "blog/clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform.html": ("Artemis Resume Builder", "a self-evolving intelligence platform case study"),
    "blog/clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform.html": ("Artemis Palantir Intelligence Blueprint", "the governed Gotham, Foundry, AIP and Apollo implementation architecture"),
    "blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html": ("Self-Evolving AI Platforms", "how Artemis improves itself safely"),
    "blog/cybersecurity-architecture-for-agentic-software.html": ("Security Architecture for Agentic Software", "designing defenses for autonomous systems"),
    "blog/ethical-sales-system-100k-revenue-prompt.html": ("Ethical Sales Psychology", "a 100K revenue system prompt"),
    "blog/frontier-intelligence-briefing-quantum-gravity-asi-biosecurity.html": ("Frontier Intelligence Briefing", "quantum gravity, ASI timelines, biosecurity"),
    "blog/post-quantum-security-advisor-clearglass-artemis.html": ("Post-Quantum Security Advisor", "the ClearGlass Artemis PQC migration wedge"),
    "blog/master-investigator-legal-tech-osint-government-accountability.html": ("Master Investigator", "legal-tech OSINT for government accountability"),
    "blog/osint-workflow-that-survives-contact-with-reality.html": ("The OSINT Workflow That Survives Contact With Reality", "field-tested investigation practice"),
    "blog/ontario-accountability-sealed-evidence.html": ("They Sealed the Evidence", "a source-led Ontario accountability brief"),
    "blog/resume-builder.html": ("Resume Builder", "PDF-export resume tool"),
    "blog/zero-trust-is-outdated.html": ("Zero Trust Is Outdated", "the original argument"),
    "blog/zero-trust-is-outdated-adaptive-trust.html": ("The Case for Adaptive Trust", "zero trust, revisited for agentic systems"),
    "blog/rethinking-security-age-of-ai-cyber-stack.html": ("Rethinking Security for the AI Cyber Stack", "a long read on defending AI-era infrastructure"),
    "blog/shadow-ai-enterprise-security-blind-spot.html": ("Shadow AI: Enterprise Security’s Biggest Blind Spot", "the unsanctioned-AI exposure most estates cannot see"),
    "blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html": ("Digital Twin Tools for Storm-Adaptive Transit", "the 2026 platform comparison and hybrid architecture"),
    "blog/coffee-and-technology-digital-revolution.html": ("Coffee & Technology", "how coffee culture and technology grew together"),
    "blog/chatgpt-prompt-shortcuts-supercharge-ai-results.html": ("ChatGPT Prompt Shortcuts", "a practical field guide to clearer, faster AI prompts"),
    "blog/ai-generated-phishing-54-percent-click-rate.html": ("AI-Generated Phishing Hits a 54% Click Rate", "this week's long read on why identity beats detection"),
    "blog/telecommunications-legal-briefing-30-july-2026.html": ("Telecommunications Legal Briefing", "a source-led Canadian telecommunications law briefing"),
    "blog/canada-digital-control-architecture-charter.html": ("Canada’s Digital-Control Architecture", "a source-led analysis of safety, surveillance and the Charter"),
    "blog/greenbelt-92-percent-access-beats-process.html": ("92%: When Access Beats Process", "a source-led Ontario Greenbelt accountability brief"),
    "blog/clearglassinc-artemis-full-stack-ai-intelligence-platform-blueprint.html": ("Artemis Full-Stack AI Blueprint", "the production architecture for a governed intelligence platform"),
    "blog/clearglass-workplace-surveillance-intelligence-defense-system.html": ("Workplace Surveillance Intelligence & Defense", "defensive research for worker rights, privacy and accountability"),
    "blog/network-orchestration-ai-automation-cybersecurity.html": ("AI-Driven Network Orchestration", "a field guide to safe, governed network automation"),
    "blog/ontario-influence-environment-august-2026.html": ("Ontario Influence Environment", "verification-first Ontario public-interest intelligence"),
    "blog/shadow-ai-incident-response-logs-gone.html": ("Shadow AI Incident Response", "forensic readiness before security evidence disappears"),
}

# --------------------------------------------------------------------------
# Pillar-and-cluster structure. Member order matters: sibling links rotate
# through this order so every page receives inbound links.
# cluster id -> {name, pillar, members, cta: [(path, label), ...]}
# --------------------------------------------------------------------------
CTA_STORE = ("store.html", "Book a security engagement")
CTA_PRICING = ("pricing.html", "See pricing & plans")
CTA_OFFERS = ("offers/index.html", "Browse services & engagements")

CLUSTERS: dict[str, dict] = {
    "security": {
        "name": "Cyber Defense & Security Operations",
        "pillar": "cyber-defense-console.html",
        "members": [
            "sentinel.html", "bluedesk.html", "guardian.html",
            "artemis-blue-team.html", "stegoforge.html",
            "attack-prompt-core.html", "environmental-cyber-risk.html",
            "bluedesk-mobile.html",
        ],
        "cta": [CTA_STORE, ("offers/security-quick-audit.html", "Start with the $249 Security Quick-Audit")],
    },
    "intelligence": {
        "name": "Intelligence & OSINT",
        "pillar": "intelligence.html",
        "members": [
            "flowsint.html", "clearglass-nexus.html", "Ontario-osint.html",
            "clearglass.html", "intelligence-command-surface.html",
            "intelligence-interface.html", "intelligence-platform.html",
            "ClearGlass-NEXUS-v12-FINAL.html", "artemis.html", "xenolith.html",
            "docs/guardian_command_nexus_spec.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
    "artemis": {
        "name": "Artemis Platform",
        "pillar": "artemis-os.html",
        "members": [
            "artemis-iv.html", "artemis-ai-cyber-intelligence-platform.html",
            "artemis-self-evolving-platform.html", "artemis-2040.html",
            "artemis-fawl/index.html",
            "air-control.html", "air-systems-control.html",
        ],
        "cta": [CTA_PRICING, CTA_STORE],
    },
    "command": {
        "name": "Command & Autonomous Operations",
        "pillar": "percival-os.html",
        "members": [
            "artemis-percival.html", "agentmesh.html", "ai-operator.html",
            "advanced-features-tools-systems.html", "automap.html",
            "conduit.html", "postloop.html", "command-console.html",
            "control-surface.html", "systems.html", "saas-platform.html",
            "CG-os.html", "percival-build.html", "clearsight.html",
            "command-center.html",
        ],
        "cta": [CTA_OFFERS, CTA_PRICING],
    },
    "legal": {
        "name": "Legal, Tax & Compliance",
        "pillar": "legal/index.html",
        "members": [
            "aegis.html", "corporate-legal-advisor.html",
            "banking-law-advisor.html", "tax.html",
            "procurement-legal-tech.html", "legal/ai-liability.html",
            "legal/legal-council.html", "legal/privacy.html",
            "legal/terms.html", "legal/articles.html", "legal/bylaws.html",
            "legal/nda.html", "legal/ip-assignment.html",
            "legal/directors-resolution.html", "legal/banking-resolution.html",
            "legal/share-subscription.html", "legal/content-policy.html",
            "legal/accessibility.html",
        ],
        "cta": [CTA_STORE, CTA_OFFERS],
    },
    "healthcare": {
        "name": "Healthcare Intelligence",
        "pillar": "clearpulse.html",
        "members": [
            "clearpulse-architecture.html", "offers/phipa-readiness.html",
            "offers/phipa-readiness-checklist.html",
        ],
        "cta": [("offers/phipa-readiness.html", "Get the free PHIPA readiness checklist"), CTA_STORE],
    },
    "government": {
        "name": "Government & Procurement",
        "pillar": "government.html",
        "members": [
            "operations/procurement-readiness.html",
            "operations/federal-supplier-handoff.html",
            "counter-uas-commercialization-os.html",
            "traffic-enforcement.html",
            "sats-digital-twin.html",
        ],
        "cta": [CTA_STORE, ("operations/procurement-readiness.html", "Check our procurement readiness")],
    },
    "services": {
        "name": "Services & Engagements",
        "pillar": "offers/index.html",
        "members": [
            "store.html", "pricing.html", "plans.html", "workspace.html",
            "checkout/index.html", "seo-authority-hub.html",
            "smb-cyber-trust-kit.html",
            "smb.html", "offers/security-quick-audit.html",
            "offers/autonomous-threat-modeling.html", "offers/hardening-sprint.html",
            "offers/guardian-command-nexus-blueprint.html", "revenue-engine.html",
            "side-store.html", "products.html",
            "business-productivity-suite.html", "global-growth-engine.html",
            "apps/command-center/index.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
    "design": {
        "name": "Web Design & UI Engineering",
        "pillar": "web-design.html",
        "members": [
            "ultra-glass.html", "clearglass-ultra.html", "futuristic.html",
            "button-lab.html", "button-system.html", "hover-menu.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
    "opal": {
        "name": "Opal-Koboi Automation",
        "pillar": "opal/index.html",
        "members": [
            "products/opal-koboi/index.html",
            "products/opal-koboi/artemis-iv-core.html",
            "products/opal-koboi/artemis-vi.html",
            "products/opal-koboi/guardian.html",
            "products/opal-koboi/revenue-engine.html",
            "products/opal-koboi/smb-suite.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
    "blog": {
        "name": "ClearGlass Intelligence · Insights",
        "pillar": "blog/index.html",
        "members": [
            "blog/autonomous-threat-modeling-2026.html",
            "blog/ai-agent-governance-governed-autonomy.html",
            "blog/clearglass-platform-audit-2026.html",
            "blog/ai-agents-insider-threat.html",
            "blog/cybersecurity-architecture-for-agentic-software.html",
            "blog/zero-trust-is-outdated-adaptive-trust.html",
            "blog/rethinking-security-age-of-ai-cyber-stack.html",
            "blog/shadow-ai-enterprise-security-blind-spot.html",
            "blog/zero-trust-is-outdated.html",
            "blog/clearglass-secure-deployment-agent.html",
            "blog/clearglass-command-center-cyber-defense-console.html",
            "blog/clearglass-agentops-microsoft-foundry-future-stack.html",
            "blog/osint-workflow-that-survives-contact-with-reality.html",
            "blog/ontario-accountability-sealed-evidence.html",
            "blog/master-investigator-legal-tech-osint-government-accountability.html",
            "blog/frontier-intelligence-briefing-quantum-gravity-asi-biosecurity.html",
            "blog/post-quantum-security-advisor-clearglass-artemis.html",
            "blog/clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform.html",
            "blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html",
            "blog/clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform.html",
            "blog/resume-builder.html",
            "blog/artemis-governed-ai-gtm-visual-growth-engine.html",
            "blog/clearglassinc-0-to-1m-corporate-execution-plan.html",
            "blog/ethical-sales-system-100k-revenue-prompt.html",
            "blog/almach-scalp-engine.html",
            "blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html",
            "blog/coffee-and-technology-digital-revolution.html",
            "blog/chatgpt-prompt-shortcuts-supercharge-ai-results.html",
            "blog/ai-generated-phishing-54-percent-click-rate.html",
            "blog/telecommunications-legal-briefing-30-july-2026.html",
            "blog/canada-digital-control-architecture-charter.html",
            "blog/greenbelt-92-percent-access-beats-process.html",
            "blog/clearglass-workplace-surveillance-intelligence-defense-system.html",
            "blog/clearglassinc-artemis-full-stack-ai-intelligence-platform-blueprint.html",
            "blog/network-orchestration-ai-automation-cybersecurity.html",
            "blog/ontario-influence-environment-august-2026.html",
            "blog/shadow-ai-incident-response-logs-gone.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
    "company": {
        "name": "Company & Operations",
        "pillar": "index.html",
        "members": [
            "investors/index.html", "authority-network.html", "operations/client-onboarding.html",
            "operations/hubspot-handoff.html",
            "operations/ontario-incorporation-handoff.html",
            "operations/stripe-handoff.html",
        ],
        "cta": [CTA_STORE, CTA_PRICING],
    },
}

# Curated cross-cluster bridges: page -> extra related targets.
# Blog posts point at the product page their topic sells; product pages point
# at the essay or adjacent cluster that deepens the topic.
EXTRA_LINKS: dict[str, list[str]] = {
    "sentinel.html": ["intelligence.html"],
    "authority-network.html": [cluster["pillar"] for cluster in CLUSTERS.values() if cluster["pillar"] != "index.html"],
    "advanced-features-tools-systems.html": ["automap.html", "percival-os.html", "agentmesh.html", "blog/autonomous-threat-modeling-2026.html"],
    "automap.html": ["advanced-features-tools-systems.html", "conduit.html", "agentmesh.html", "intelligence-command-surface.html"],
    "cyber-defense-console.html": ["blog/clearglass-command-center-cyber-defense-console.html", "smb-cyber-trust-kit.html"],
    "bluedesk.html": ["blog/ai-agents-insider-threat.html"],
    "percival-os.html": ["blog/ai-agent-governance-governed-autonomy.html"],
    "agentmesh.html": ["blog/cybersecurity-architecture-for-agentic-software.html", "flowsint.html"],
    "ai-operator.html": ["artemis-self-evolving-platform.html", "blog/ai-agent-governance-governed-autonomy.html"],
    "conduit.html": ["blog/clearglass-agentops-microsoft-foundry-future-stack.html"],
    "flowsint.html": ["blog/osint-workflow-that-survives-contact-with-reality.html", "agentmesh.html", "cyber-defense-console.html"],
    "intelligence.html": ["authority-network.html", "blog/frontier-intelligence-briefing-quantum-gravity-asi-biosecurity.html"],
    "xenolith.html": ["percival-os.html", "agentmesh.html", "advanced-features-tools-systems.html", "blog/ai-agent-governance-governed-autonomy.html"],
    "artemis-os.html": ["artemis-percival.html", "blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html"],
    "artemis-self-evolving-platform.html": ["blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html"],
    "revenue-engine.html": ["postloop.html", "blog/ethical-sales-system-100k-revenue-prompt.html"],
    "government.html": ["procurement-legal-tech.html"],
    "counter-uas-commercialization-os.html": ["air-control.html"],
    "traffic-enforcement.html": ["air-control.html"],
    "sats-digital-twin.html": ["blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html", "environmental-cyber-risk.html"],
    "procurement-legal-tech.html": ["government.html", "blog/master-investigator-legal-tech-osint-government-accountability.html"],
    "clearpulse.html": ["environmental-cyber-risk.html"],
    "web-design.html": ["offers/index.html"],
    "smb-cyber-trust-kit.html": ["offers/hardening-sprint.html"],
    "store.html": ["smb-cyber-trust-kit.html"],
    "products.html": ["offers/index.html", "advanced-features-tools-systems.html", "store.html"],
    "opal/index.html": ["conduit.html"],
    "products/opal-koboi/artemis-iv-core.html": ["artemis-iv.html"],
    "products/opal-koboi/artemis-vi.html": ["artemis-os.html"],
    "products/opal-koboi/guardian.html": ["guardian.html"],
    "products/opal-koboi/revenue-engine.html": ["revenue-engine.html"],
    "products/opal-koboi/smb-suite.html": ["smb.html"],
    # blog -> product conversion bridges
    "blog/autonomous-threat-modeling-2026.html": ["offers/autonomous-threat-modeling.html", "cyber-defense-console.html", "agentmesh.html", "blog/cybersecurity-architecture-for-agentic-software.html"],
    "offers/autonomous-threat-modeling.html": ["blog/autonomous-threat-modeling-2026.html", "cyber-defense-console.html", "bluedesk.html", "offers/index.html"],
    "blog/ai-agent-governance-governed-autonomy.html": ["percival-os.html", "ai-operator.html"],
    "blog/ai-agents-insider-threat.html": ["bluedesk.html", "cyber-defense-console.html"],
    "blog/cybersecurity-architecture-for-agentic-software.html": ["agentmesh.html", "cyber-defense-console.html"],
    "blog/zero-trust-is-outdated-adaptive-trust.html": ["cyber-defense-console.html"],
    "blog/zero-trust-is-outdated.html": ["blog/zero-trust-is-outdated-adaptive-trust.html", "cyber-defense-console.html"],
    "blog/clearglass-platform-audit-2026.html": ["ai-operator.html", "advanced-features-tools-systems.html", "blog/ai-agent-governance-governed-autonomy.html"],
    "blog/clearglass-secure-deployment-agent.html": ["percival-os.html", "blog/clearglass-platform-audit-2026.html"],
    "blog/clearglass-command-center-cyber-defense-console.html": ["cyber-defense-console.html"],
    "blog/clearglass-agentops-microsoft-foundry-future-stack.html": ["conduit.html", "agentmesh.html"],
    "blog/osint-workflow-that-survives-contact-with-reality.html": ["flowsint.html", "intelligence.html"],
    "blog/ontario-accountability-sealed-evidence.html": ["flowsint.html", "procurement-legal-tech.html", "blog/master-investigator-legal-tech-osint-government-accountability.html"],
    "blog/master-investigator-legal-tech-osint-government-accountability.html": ["flowsint.html", "procurement-legal-tech.html"],
    "blog/frontier-intelligence-briefing-quantum-gravity-asi-biosecurity.html": ["intelligence.html", "blog/post-quantum-security-advisor-clearglass-artemis.html"],
    "blog/post-quantum-security-advisor-clearglass-artemis.html": ["intelligence.html", "cyber-defense-console.html"],
    "blog/clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform.html": ["advanced-features-tools-systems.html", "artemis-self-evolving-platform.html", "artemis-os.html"],
    "blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html": ["artemis-self-evolving-platform.html", "artemis-os.html"],
    "blog/clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform.html": ["blog/resume-builder.html", "artemis-self-evolving-platform.html"],
    "blog/resume-builder.html": ["blog/clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform.html"],
    "blog/artemis-governed-ai-gtm-visual-growth-engine.html": ["artemis-os.html", "revenue-engine.html"],
    "blog/clearglassinc-0-to-1m-corporate-execution-plan.html": ["revenue-engine.html", "legal/index.html"],
    "blog/ethical-sales-system-100k-revenue-prompt.html": ["revenue-engine.html"],
    "blog/almach-scalp-engine.html": ["revenue-engine.html"],
    "blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html": ["sats-digital-twin.html", "environmental-cyber-risk.html"],
    "blog/coffee-and-technology-digital-revolution.html": ["advanced-features-tools-systems.html", "blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html"],
    "blog/chatgpt-prompt-shortcuts-supercharge-ai-results.html": ["ai-operator.html", "blog/ai-agent-governance-governed-autonomy.html"],
    "blog/ai-generated-phishing-54-percent-click-rate.html": ["guardian.html", "blog/ai-agents-insider-threat.html"],
    "blog/canada-digital-control-architecture-charter.html": ["legal/index.html", "aegis.html", "blog/telecommunications-legal-briefing-30-july-2026.html"],
    "artemis-fawl/index.html": ["artemis-os.html", "artemis-self-evolving-platform.html"],
    "blog/greenbelt-92-percent-access-beats-process.html": ["blog/index.html", "Ontario-osint.html"],
    "blog/clearglassinc-artemis-full-stack-ai-intelligence-platform-blueprint.html": ["blog/index.html", "artemis-iv.html"],
    "blog/network-orchestration-ai-automation-cybersecurity.html": ["conduit.html", "agentmesh.html", "cyber-defense-console.html"],
    "apps/command-center/index.html": ["revenue-engine.html", "offers/index.html"],
}

SIBLING_WINDOW = 4     # rotated sibling links per member page
PILLAR_MAX_MEMBERS = 10  # member links shown on a pillar page

# Full-viewport HUD pages whose body{overflow:hidden} would strand a normal
# bottom block; these get a fixed corner chip that expands the same panel on
# hover/focus (pure CSS), mirroring the site's existing nav.js edge-tab pattern.
FIXED_VIEWPORT = {
    "sentinel.html", "clearglass.html", "air-control.html",
    "percival-os.html", "artemis-percival.html", "percival-build.html",
    "clearsight.html",
}

CSS = (
    "#cg-related{margin:54px auto 0;max-width:1120px;padding:0 18px 38px;"
    "font-family:'Inter',system-ui,-apple-system,sans-serif;position:relative}"
    "#cg-related .cgr-box{position:relative;overflow:hidden;background:"
    "linear-gradient(rgba(34,211,238,.055) 1px,transparent 1px),"
    "linear-gradient(90deg,rgba(124,150,255,.05) 1px,transparent 1px),"
    "radial-gradient(circle at 12% 0,rgba(34,211,238,.16),transparent 34%),"
    "radial-gradient(circle at 88% 100%,rgba(168,85,247,.16),transparent 36%),"
    "linear-gradient(165deg,rgba(5,12,28,.97),rgba(9,7,24,.97));"
    "background-size:32px 32px,32px 32px,auto,auto,auto;border:1px solid rgba(34,211,238,.34);"
    "border-radius:16px;padding:24px 26px;color:#d8e4ff;"
    "box-shadow:0 18px 54px rgba(0,0,0,.44),0 0 34px rgba(34,211,238,.12),inset 0 0 0 1px rgba(255,255,255,.035)}"
    "#cg-related .cgr-box:before{content:'';position:absolute;inset:0;pointer-events:none;"
    "background:linear-gradient(90deg,transparent,rgba(34,211,238,.18),transparent);"
    "transform:translateX(-120%) skewX(-18deg);animation:cgr-scan 8s ease-in-out infinite}"
    "#cg-related .cgr-box:after{content:'';position:absolute;left:24px;right:24px;top:0;height:1px;"
    "background:linear-gradient(90deg,transparent,#22d3ee,#a855f7,transparent);box-shadow:0 0 18px rgba(34,211,238,.75)}"
    "#cg-related .cgr-crumb{position:relative;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;"
    "color:#8fb9ff;margin:0 0 12px}"
    "#cg-related .cgr-crumb a{color:#67e8f9;text-decoration:none;text-shadow:0 0 12px rgba(34,211,238,.35)}"
    "#cg-related .cgr-crumb a:hover{color:#fff;text-decoration:none}"
    "#cg-related h2{position:relative;margin:0 0 14px;font-size:15.5px;letter-spacing:.08em;text-transform:uppercase;color:#f3f7ff}"
    "#cg-related .cgr-route{position:relative;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 16px}"
    "#cg-related .cgr-route a{display:flex;min-height:46px;align-items:center;padding:8px 10px;border-radius:10px;"
    "background:rgba(7,14,32,.52);border:1px solid rgba(124,150,255,.15);color:#cfe0ff;text-decoration:none;font-size:12px;line-height:1.35}"
    "#cg-related .cgr-route a:hover,#cg-related .cgr-route a:focus-visible{border-color:#22d3ee;color:#fff;box-shadow:0 0 18px rgba(34,211,238,.14)}"
    "#cg-related .cgr-route b{display:block;color:#67e8f9;font-size:9px;letter-spacing:.16em;text-transform:uppercase;margin-bottom:2px}"
    "#cg-related ul{position:relative;list-style:none;margin:0;padding:0;display:grid;"
    "grid-template-columns:repeat(auto-fit,minmax(248px,1fr));gap:8px 18px}"
    "#cg-related li a{display:block;padding:9px 11px;border-radius:10px;font-size:13.5px;"
    "line-height:1.45;color:#cfe0ff;text-decoration:none;border:1px solid rgba(124,150,255,.08);"
    "background:rgba(7,14,32,.36);transition:transform .14s ease,border-color .14s ease,background .14s ease,box-shadow .14s ease}"
    "#cg-related li a:hover,#cg-related li a:focus-visible{transform:translateY(-1px);background:rgba(34,211,238,.1);border-color:rgba(34,211,238,.42);"
    "color:#fff;box-shadow:0 0 22px rgba(34,211,238,.14)}"
    "#cg-related li a b{color:#9bdcff;font-weight:700;text-shadow:0 0 12px rgba(34,211,238,.28)}"
    "#cg-related .cgr-cta{position:relative;margin:16px 0 0;padding-top:14px;border-top:1px solid rgba(34,211,238,.18);"
    "font-size:13.5px;color:#a9b8df}"
    "#cg-related .cgr-cta a{color:#67e8f9;font-weight:700;text-decoration:none;border-bottom:1px solid rgba(34,211,238,.36)}"
    "#cg-related .cgr-cta a:hover{color:#fff;border-bottom-color:#fff}"
    "@media(max-width:620px){#cg-related .cgr-box{padding:21px 17px}#cg-related .cgr-route{grid-template-columns:1fr}"
    "#cg-related ul{grid-template-columns:1fr}}"
    "@keyframes cgr-scan{0%,58%{transform:translateX(-120%) skewX(-18deg);opacity:0}70%{opacity:1}100%{transform:translateX(220%) skewX(-18deg);opacity:0}}"
    "@media(prefers-reduced-motion:reduce){#cg-related .cgr-box:before{animation:none}}"
)

DOCK_CSS = (
    "#cg-related.cgr-dock{position:fixed;left:14px;bottom:14px;margin:0;padding:0;"
    "max-width:none;z-index:2147483000}"
    "#cg-related.cgr-dock .cgr-tab{display:inline-block;cursor:pointer;font-size:10.5px;"
    "letter-spacing:.22em;text-transform:uppercase;color:#dbe4ff;padding:8px 12px;"
    "border-radius:9px;border:1px solid rgba(124,150,255,.42);"
    "background:linear-gradient(180deg,rgba(18,20,42,.92),rgba(11,12,28,.92));"
    "box-shadow:0 6px 22px rgba(0,0,0,.4);backdrop-filter:blur(6px);user-select:none}"
    "#cg-related.cgr-dock .cgr-tab:hover{color:#fff;border-color:rgba(124,150,255,.85)}"
    "#cg-related.cgr-dock .cgr-box{display:none;position:absolute;bottom:calc(100% + 8px);"
    "left:0;width:min(400px,92vw);max-height:62vh;overflow-y:auto}"
    "#cg-related.cgr-dock:hover .cgr-box,#cg-related.cgr-dock:focus-within .cgr-box{display:block}"
    "#cg-related.cgr-dock ul{grid-template-columns:1fr}"
)


def rel(from_page: str, to_page: str) -> str:
    """Relative href from one site path to another."""
    start = posixpath.dirname(from_page) or "."
    return posixpath.relpath(to_page, start)


def anchor(from_page: str, to_page: str) -> str:
    title, desc = PAGES[to_page]
    return (
        f'<li><a href="{html.escape(rel(from_page, to_page), quote=True)}">'
        f"<b>{html.escape(title)}</b> — {html.escape(desc)}</a></li>"
    )


def cluster_of(page: str) -> str:
    for cid, c in CLUSTERS.items():
        if page == c["pillar"] or page in c["members"]:
            return cid
    raise KeyError(f"page not in any cluster: {page}")


def related_targets(page: str) -> tuple[list[str], list[tuple[str, str]], str]:
    """Return (related pages, cta pairs, crumb-pillar path) for a page."""
    cid = cluster_of(page)
    c = CLUSTERS[cid]
    ids = list(CLUSTERS)

    if page == "index.html":  # site hub: link every pillar
        targets = [CLUSTERS[i]["pillar"] for i in ids if CLUSTERS[i]["pillar"] != page]
        return targets, c["cta"], ""

    if page == c["pillar"]:
        targets = list(c["members"][:PILLAR_MAX_MEMBERS])
        # two sibling pillars, rotated by this cluster's position
        k = ids.index(cid)
        for off in (1, 2):
            targets.append(CLUSTERS[ids[(k + off) % len(ids)]]["pillar"])
    else:
        members = c["members"]
        i = members.index(page)
        n = len(members)
        window = min(SIBLING_WINDOW, n - 1)
        targets = [members[(i + off) % n] for off in range(1, window + 1)]

    seen, out = {page}, []
    for t in EXTRA_LINKS.get(page, []) + targets:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out, c["cta"], c["pillar"] if page != c["pillar"] else ""


def journey_targets(page: str) -> tuple[str, str, str]:
    """Return the previous, hub and next destinations in a page's cluster."""
    cluster = CLUSTERS[cluster_of(page)]
    route = [cluster["pillar"], *cluster["members"]]
    position = route.index(page)
    previous = route[position - 1] if position else route[-1]
    following = route[(position + 1) % len(route)]
    return previous, cluster["pillar"], following


def route_link(page: str, target: str, label: str) -> str:
    title = PAGES[target][0]
    return (
        f'<a href="{html.escape(rel(page, target), quote=True)}">'
        f'<span><b>{html.escape(label)}</b>{html.escape(title)}</span></a>'
    )


def build_block(page: str) -> str:
    targets, cta, pillar = related_targets(page)
    cid = cluster_of(page)
    name = CLUSTERS[cid]["name"]

    crumb = f'<a href="{html.escape(rel(page, "index.html"), quote=True)}">ClearGlass Inc.</a>'
    if page == "index.html":
        crumb += " · Site network"
        heading = "Explore the ClearGlass network"
    elif pillar:
        crumb += (
            f' › <a href="{html.escape(rel(page, pillar), quote=True)}">{html.escape(name)}</a>'
        )
        heading = "Continue exploring"
    else:
        crumb += f" › {html.escape(name)}"
        heading = f"Inside {name}"

    items = "\n      ".join(anchor(page, t) for t in targets)
    previous, hub, following = journey_targets(page)
    route = "\n      ".join((
        route_link(page, previous, "Previous"),
        route_link(page, hub, "Topic hub"),
        route_link(page, following, "Next in journey"),
    ))
    cta_html = " · ".join(
        f'<a href="{html.escape(rel(page, path), quote=True)}">{html.escape(label)}</a>'
        for path, label in cta
    )

    docked = page in FIXED_VIEWPORT
    css = CSS + DOCK_CSS if docked else CSS
    cls = ' class="cgr-dock"' if docked else ""
    tab = (
        '  <div class="cgr-tab" tabindex="0" role="button" '
        'aria-label="Show related ClearGlass pages">⌁ Explore ClearGlass</div>\n'
        if docked else ""
    )

    return (
        f"{START}\n"
        f'<aside id="cg-related"{cls}>\n'
        f"  <style>{css}</style>\n"
        f'  <nav class="cgr-box" aria-label="Related ClearGlass pages">\n'
        f'    <p class="cgr-crumb">{crumb}</p>\n'
        f"    <h2>{html.escape(heading)}</h2>\n"
        f'    <div class="cgr-route" aria-label="Journey navigation">\n      {route}\n    </div>\n'
        f"    <ul>\n      {items}\n    </ul>\n"
        f'    <p class="cgr-cta">Next step: {cta_html}</p>\n'
        f"  </nav>\n"
        f"{tab}"
        f"</aside>\n"
        f"{END}"
    )


BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)


def inject(page: str) -> tuple[bool, str]:
    """Insert or refresh the block in a page. Returns (changed, status)."""
    path = ROOT / page
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    block = build_block(page)

    if BLOCK_RE.search(text):
        new = BLOCK_RE.sub(lambda _: block, text, count=1)
        status = "refreshed"
    else:
        idx = text.lower().rfind("</body>")
        if idx == -1:
            return False, "SKIP: no </body>"
        new = text[:idx] + block + "\n" + text[idx:]
        status = "injected"

    if new == text:
        return False, "unchanged"
    path.write_text(new, encoding="utf-8", errors="surrogateescape")
    return True, status


def validate() -> list[str]:
    errors = []
    clustered = set()
    for cid, c in CLUSTERS.items():
        for p in [c["pillar"], *c["members"]]:
            if p in clustered and p != "index.html":
                errors.append(f"{p}: in more than one cluster")
            clustered.add(p)
            if p not in PAGES:
                errors.append(f"{cid}: {p} missing from PAGES")
    for p in PAGES:
        if p not in clustered:
            errors.append(f"{p}: in PAGES but no cluster")
        if not (ROOT / p).is_file():
            errors.append(f"{p}: file not found")
    for src, targets in EXTRA_LINKS.items():
        for t in [src, *targets]:
            if t not in PAGES:
                errors.append(f"EXTRA_LINKS: unknown page {t}")
    overlap = set(PAGES) & set(EXCLUDED_PAGES)
    for page in sorted(overlap):
        errors.append(f"{page}: both mapped and excluded")
    discovered = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.html")
        if not {".git", "node_modules", ".next"} & set(path.parts)
    }
    classified = set(PAGES) | set(EXCLUDED_PAGES)
    for page in sorted(discovered - classified):
        errors.append(f"{page}: HTML page is not classified")
    for page in sorted(set(EXCLUDED_PAGES) - discovered):
        errors.append(f"{page}: excluded HTML page not found")
    return errors


def build_report() -> str:
    """Build the human-readable, page-by-page information architecture map."""
    lines = [
        "# ClearGlass Site-Wide Wiring Plan",
        "",
        "> Generated by `python3 tools/internal_links.py`. Edit the site graph in that generator, not this report.",
        "",
        "## Experience architecture",
        "",
        "Every mapped page keeps its original content and receives one additive, crawlable journey module immediately before `</body>`. The module provides a Home/topic breadcrumb, a deterministic previous–hub–next route, contextual related pages, and two conversion paths. Fixed-viewport command surfaces use the same module as a keyboard-focusable corner dock so their canvas remains intact.",
        "",
        "The journey model is: **discover → orient in a topic hub → explore an adjacent capability → deepen through evidence → choose a governed engagement**. High-risk operational actions remain outside this marketing navigation and retain their existing human-approval boundaries.",
        "",
        "## Additive navigation system",
        "",
        "- **Breadcrumb:** Home and the current topic pillar provide location and semantic hierarchy.",
        "- **Journey rail:** Previous, topic hub, and next links create a predictable cinematic sequence.",
        "- **Related module:** Rotated sibling links distribute discovery across every page in a cluster; curated bridges connect adjacent clusters.",
        "- **CTA bridge:** Each cluster ends in two relevant, non-coercive next steps such as offers, pricing, readiness, or booking.",
        "- **Responsive behavior:** Three route cards collapse to one column below 620px; related cards use an adaptive grid; motion is disabled when reduced motion is requested.",
        "- **SEO and accessibility:** Links are static HTML, labels are descriptive, navigation landmarks are named, focus states are visible, and all routes remain unchanged.",
        f"- **Audit coverage:** {len(PAGES)} public pages are connected and {len(EXCLUDED_PAGES)} utility, completion, prototype, or private pages are explicitly excluded.",
        "",
        "## Page-by-page flow map",
        "",
        "| Page | Role | Previous | Topic hub | Next | Conversion bridge |",
        "|---|---|---|---|---|---|",
    ]
    for cluster in CLUSTERS.values():
        lines.append(f"| **{cluster['name']}** | **Topic cluster** |  |  |  |  |")
        for page in [cluster["pillar"], *cluster["members"]]:
            previous, hub, following = journey_targets(page)
            title, description = PAGES[page]
            ctas = " / ".join(label for _, label in cluster["cta"])
            lines.append(
                f"| `{page}` — {title} | {description} | {PAGES[previous][0]} | "
                f"{PAGES[hub][0]} | {PAGES[following][0]} | {ctas} |"
            )
    lines.extend((
        "", "## Explicitly excluded surfaces", "",
        "These pages remain intact but are not eligible for generated journey updates. Existing markup is preserved; excluding them prevents future search leakage, conversion loops after form completion, and interference with loaders or recovery states.",
        "", "| Page | Role | Exclusion rationale |", "|---|---|---|",
    ))
    for page, (role, reason) in EXCLUDED_PAGES.items():
        lines.append(f"| `{page}` | {role} | {reason} |")
    lines.extend((
        "", "## Implementation and verification strategy", "",
        "1. Maintain page metadata, cluster membership, curated bridges, and fixed-viewport exceptions in `tools/internal_links.py`.",
        "2. Run `python3 tools/internal_links.py` after any page is added, renamed, or repositioned. This regenerates both HTML modules and this report.",
        "3. Run `python3 tools/internal_links.py --check` in review to reject stale generated modules or a stale flow map.",
        "4. Validate local destinations, semantic landmarks, keyboard focus, mobile layout, reduced motion, and browser-console output before Pages deployment.",
        "5. Roll back by reverting the generator commit and regenerating; original page content is never rewritten outside the delimited `cg-related` block.",
        "", "## Growth rule", "",
        "New pages must be assigned one clear journey role, one topic cluster, previous/next adjacency, descriptive anchors, and a governed conversion bridge. This keeps the experience extensible without flattening product, editorial, operational, or legal content.", "",
    ))
    return "\n".join(lines)


def main() -> int:
    check = "--check" in sys.argv
    errors = validate()
    if errors:
        print("site map errors:")
        for e in errors:
            print("  -", e)
        return 1

    changed = 0
    for page in PAGES:
        if check:
            text = (ROOT / page).read_text(encoding="utf-8", errors="surrogateescape")
            m = BLOCK_RE.search(text)
            if not m or m.group(0) != build_block(page):
                print(f"stale: {page}")
                changed += 1
        else:
            did, status = inject(page)
            if did:
                changed += 1
            if status.startswith("SKIP"):
                print(f"{status}: {page}")

    report = build_report()
    current_report = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
    if check:
        if current_report != report:
            print(f"stale: {REPORT_PATH.name}")
            changed += 1
    elif current_report != report:
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"generated: {REPORT_PATH.name}")

    if check:
        print(f"{changed} page(s) stale" if changed else f"all {len(PAGES)} pages current")
        return 1 if changed else 0
    print(f"{changed} page(s) updated, {len(PAGES) - changed} already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
