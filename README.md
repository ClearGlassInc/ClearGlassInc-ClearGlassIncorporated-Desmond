# ClearGlass Engineering and Marketing Agent Army

A deterministic, dependency-free planning control plane that routes software, operations, marketing, and revenue objectives across specialized agents while keeping external side effects behind explicit human approval.

This package does **not** publish posts, send messages, spend money, deploy production systems, scrape platforms, or store credentials. It generates auditable execution plans for authorized operators and downstream tools.

## Architecture

| Division | Agent | Responsibility |
| --- | --- | --- |
| Command | Chief of Staff | Objective normalization, sequencing, dependencies, decisions |
| Engineering | Staff Engineer | Architecture, implementation, maintainability, performance |
| Engineering | Quality and Security | Testing, threat/failure analysis, release and rollback gates |
| Engineering | Legacy Modernization | Legacy-system inventory, compatibility contracts, migration slices, parity and rollback evidence |
| Marketing | Market Intelligence | Audience, pain, positioning, buying signals, evidence gaps |
| Marketing | Content Strategy | Evidence-backed content systems and claim control |
| Marketing | Campaign Bot Commander | Governed bot swarm coordination for campaign workbacks, channel assets, and launch packets |
| Marketing | Distribution Planning | Channel execution queues and approval packets |
| Marketing | Revenue Operations | Offers, qualification, pipeline, conversion hypotheses |
| Command | Analytics Controller | KPI definitions, experiments, decision-ready reporting |

The ordered workflow is defined in `config.json`. The canonical behavior and safety policy is in `AGENT_POLICY.md`.

## Run locally

Python 3.11+ is sufficient; there are no third-party runtime dependencies.

```bash
python -m agent_army.orchestrator \
  --request "Build and test a secure service, then prepare a compliant revenue campaign"
```

Generate JSON for another system:

```bash
python -m agent_army.orchestrator \
  --request "Design a launch campaign for a verified ClearGlass capability" \
  --format json \
  --output artifacts/agent-army-plan.json
```

The output write is atomic. Existing output files are replaced only after the complete plan has been written successfully.

## Encrypted artifact mode

Sensitive plans can be piped directly into the Rust secure runtime so plaintext is never written to disk:

```bash
python -m agent_army.orchestrator \
  --request "Build and market the secure workflow product" \
  --format json |
  ./agent_army/secure_runtime/target/release/clearglass-secure encrypt \
    --recipient ./agent-army.recipient \
    --input - \
    --output ./artifacts/agent-army-plan.json.age
```

The Rust sidecar uses interoperable `age` encryption with X25519 recipients, authenticated tamper detection, strict input limits, no-overwrite output semantics, and restricted Unix permissions for private identities and decrypted files. See [`secure_runtime/README.md`](secure_runtime/README.md) for key generation, build, recovery, rotation, and decryption procedures.

Private identities must never be committed. There is no recovery back door: loss of the identity means loss of access, and exposure requires immediate rotation.

## Routing behavior

The orchestrator uses explicit role triggers and request signals:

- Engineering requests select engineering and quality roles.
- Marketing/revenue requests select market, content, distribution, and revenue roles.
- Legacy modernization requests add compatibility, parity, migration-slice, and rollback planning so existing contracts are preserved.
- Bot-army or campaign-automation requests add the Campaign Bot Commander to coordinate channel specialists without granting publish, send, spend, or platform-control authority.
- Combined requests select the complete cross-functional chain.
- Ambiguous requests default to full-spectrum planning rather than silently omitting a required discipline.
- Chief of Staff and Analytics Controller remain present to enforce sequencing and measurable outcomes.

## Approval behavior

The plan flags approval gates when the request implies:

- external publishing;
- external outreach;
- paid spend;
- production deployment or release;
- legal, regulatory, certification, or compliance claims;
- customer or personal-data use.

Approval flags are attached to the workflow stages where the side effect could occur. Planning can continue; the flagged action cannot be treated as authorized.

## Validation

Run the focused Python test suite:

```bash
python -m unittest tests.test_agent_army -v
```

Validate the Rust cryptographic runtime:

```bash
cd agent_army/secure_runtime
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets --all-features --locked
```

The dedicated GitHub Actions workflows validate:

1. configuration integrity;
2. routing across engineering and marketing;
3. approval-gate detection;
4. deterministic plan identifiers;
5. atomic JSON output;
6. a complete sample plan;
7. Rust formatting and Clippy diagnostics;
8. cryptographic round trips, wrong-key rejection, and tamper rejection;
9. release compilation and CLI pipeline behavior;
10. Unix private-key permissions.

The repository-wide CI also discovers `tests/test_agent_army.py` through the existing test job.

## Configuration changes

When adding a role:

1. Assign a unique `id`.
2. Use one of the governed divisions: `command`, `engineering`, or `marketing`.
3. Define precise triggers and concrete deliverables.
4. Add the role to the ordered workflow.
5. Add or update tests proving routing and approval behavior.

Configuration validation fails closed on duplicate roles, duplicate stages, missing divisions, unknown workflow owners, empty triggers, empty deliverables, and malformed JSON.

## Operating rule

The agent army is a decision and execution-control system, not a license for uncontrolled automation. Evidence, authorization, security, encrypted handling, and measurable business outcomes govern every stage.
