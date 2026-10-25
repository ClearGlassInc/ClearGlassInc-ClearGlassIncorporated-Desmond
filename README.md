# ClearGlass Inc.

**Transparency Is Infrastructure.**

**AI automation · Cybersecurity · Software architecture**

ClearGlass Inc. is a Canadian technology company based in Burlington, Ontario.
We design software and automation to help organizations understand their systems,
manage digital risk, and turn complex operations into clear, accountable workflows.

This repository brings together the ClearGlass website, application source,
AI agent systems, security tooling, and supporting technical documentation.

[Website](https://www.clearglassinc.com) ·
[Contact](mailto:desmondotieno@icloud.com) ·
[Report an issue](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/issues)

## What we focus on

| Area | Focus |
| --- | --- |
| AI automation and agent systems | Workflow orchestration, decision support, human approval, and traceable execution. |
| Cybersecurity and digital risk | Access governance, defensive security workflows, and evidence-based assessment. |
| Software architecture and integration | Web applications, backend services, APIs, and connected operational data. |
| Governance and operational intelligence | Documented controls, evidence integrity, and accountable decision-making. |

Our engineering approach emphasizes transparency, security, and human oversight.
The repository includes working components, prototypes, and architecture proposals;
each component's documentation defines its scope and setup. A design document or
demo does not establish that a system is deployed or independently audited.

## Repository guide

This is a monorepo: its applications and services have separate dependencies and
deployment requirements.

| Location | Contents |
| --- | --- |
| [`index.html`](index.html), [`assets/`](assets/) | ClearGlass public website and shared assets. |
| [`app/`](app/), [`components/`](components/), [`lib/`](lib/) | Root Next.js application and supporting UI and application code. |
| [`control-plane/`](control-plane/) | FastAPI commerce and operations control plane. |
| [`storefront/`](storefront/), [`admin/`](admin/) | Separate Next.js commerce applications. |
| [`agent_os/`](agent_os/), [`agents/`](agents/) | Agent orchestration, policies, and agent definitions. |
| [`security/`](security/), [`truth_forensics/`](truth_forensics/) | Security documentation and evidence-integrity tooling. |
| [`docs/`](docs/), [`deployment/`](deployment/) | Architecture notes, component documentation, and deployment runbooks. |
| [`tests/`](tests/), [`scripts/`](scripts/), [`tools/`](tools/) | Tests, validation scripts, and maintenance tools. |

## Getting started

### Clone the repository

```bash
git clone https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond.git
cd ClearGlassInc-ClearGlassIncorporated-Desmond
```

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and
[CLAUDE.md](CLAUDE.md) before making changes.

### Preview the static website

From the repository root:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). This previews the static
pages; integrations that require a backend need their own configuration.

### Run the root Next.js application

With Node.js and npm installed, use the root [package.json](package.json):

```bash
npm ci
npm run dev
```

Open [http://localhost:3030](http://localhost:3030). Root application checks are:

```bash
npm run typecheck
npm test
npm run build
```

### Work on other components

Use the manifest and instructions for the component you intend to run.
[CLAUDE.md](CLAUDE.md) covers the commerce control plane and frontends;
[DEPLOY.md](DEPLOY.md) describes their deployment requirements.

Python tooling uses Python 3.11 as documented in [CONTRIBUTING.md](CONTRIBUTING.md).
After preparing the required Python environment, run the repository's local gates:

```bash
python3 scripts/ci_local.py
```

## Engineering and security

- Keep consequential actions behind the applicable human approval gates.
- Keep credentials in runtime configuration, outside source code and browser bundles.
- Preserve existing functionality and validate changes before opening a pull request.

Follow [CONTRIBUTING.md](CONTRIBUTING.md) for contributions and
[SECURITY.md](SECURITY.md) for vulnerability reporting.

## Additional project documentation

The educational blockchain and wallet project remains part of this repository.
Its previous README is preserved in [README-CGLASS.md](README-CGLASS.md),
alongside its [whitepaper](WHITEPAPER.md) and [technical documentation](TECHNICAL_DOCS.md).
Those materials describe that individual project within the wider ClearGlass repository.

## Company and contact

Burlington, Ontario, Canada.

- **Founder:** Desmond Otieno Odhiambo
- **Website:** [www.clearglassinc.com](https://www.clearglassinc.com)
- **Email:** [desmondotieno@icloud.com](mailto:desmondotieno@icloud.com)

## License

See [LICENSE](LICENSE) and any component-specific or third-party license notices.
