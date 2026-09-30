# ClearGlass Truth Forensics

> The ClearGlass Truth Forensics system provides analytical indicators and provenance analysis. It does not independently establish the truth of real-world events and should not replace qualified forensic, legal, investigative, or evidentiary review.

Truth Forensics is ClearGlass's evidence-integrity engine. It hashes digital evidence, records its provenance in a hash-chained ledger, and runs structural media analysis. It then tests a written claim against every independent source it can compare, and routes the result to a human reviewer.

It ships in two forms that produce byte-identical output:

| Form | Path | Runs where |
|---|---|---|
| Reference engine (Python, stdlib only) | `truth_forensics/` | CLI, tests, any server that imports it |
| Browser engine | `assets/js/truth-forensics-engine.js` (+ `-worker.js`) | The Insights console, in the visitor's browser |
| Console | `blog/truth-forensics.html`, `assets/js/truth-forensics-console.js`, `assets/css/truth-forensics.css` | GitHub Pages |
| Demonstration case | `data/truth-forensics/demo-case.json`, `data/truth-forensics/demo/` | Both engines |
| Method briefs | `blog/truth-is-an-evidence-graph.html`, `blog/deepfake-detection-needs-chain-of-custody.html`, `blog/when-ai-cannot-determine-the-truth.html` | GitHub Pages |

The concept, names and code are original to ClearGlass. Nothing here implements, or is modelled on, a fictional programme.

## 1. What it does, and what it does not

| It does | It does not |
|---|---|
| Hash every item (SHA-256) at intake and chain each custody event | Decide whether an event happened |
| Parse JPEG, PNG, WAV and ISO-BMFF (MP4/MOV) structure and metadata | Validate C2PA signatures (it detects manifest presence only) |
| Report structural indicators, each with method, confidence and limitation | Run a trained deepfake or synthetic-media classifier |
| Collapse copies and derivatives into independence groups before counting | Treat reposts or re-encodes as corroboration |
| Decompose a claim into propositions and test each one against independent groups | Fetch URLs (they are recorded as references only) |
| Require a named human decision before anything is VERIFIED | Send evidence to any external AI provider |

When no indicator fires, the report says: *No manipulation indicators detected by the available analyzers. Authenticity cannot be established solely from this analysis.* It never says "authentic".

## 2. Architecture

```text
 intake ──► hash ──► provenance ledger (hash-chained, append-only)
   │
   ├─► image.py / audio.py / video.py ── structural analysis ──► indicators
   ├─► events.py ── sensor window, clock reference, custody receipt
   │
   ▼
 correlation.py ── independence groups ── dimension comparisons
   │
   ├─► claims.py ─── propositions ─► verdict per proposition ─► claim verdict
   ├─► consistency.py ─ WHO / WHAT / WHEN / WHERE / HOW / SOURCE / PROVENANCE
   ├─► bifocal.py ─── primary media vs independent channels (heuristic score)
   ├─► timeline.py ── NORMAL / REVIEW / SUPPORTED / ANOMALY segments
   ├─► graph.py ───── evidence graph, FACTUAL vs INFERENCE edges
   │
   ▼
 case.py ── result document ─► review.py (human decisions) ─► report.py (14 sections)
```

The pipeline stages recorded for every case are fixed in `vocab.PIPELINE`: SOURCE, ACQUISITION, HASH, PROVENANCE, METADATA, CONTENT_ANALYSIS, TEMPORAL_ANALYSIS, CROSS_SOURCE_CORRELATION, MANIPULATION_INDICATORS, CONFIDENCE_ASSESSMENT, EVIDENCE_GRAPH, AUDIT_RECORD, HUMAN_REVIEW.

A job moves QUEUED → PROCESSING → ANALYZING → REVIEW_REQUIRED, then COMPLETE or FAILED.

### Why a static engine, not a server

GitHub Pages serves the site from a branch, and Actions dispatches no runners (`CLAUDE.md`, `docs/BASELINE.md` F1). A server-side analyzer would have nowhere to run. The engine therefore runs in the visitor's browser, which is also the privacy-preserving choice: evidence never leaves the device. The Python engine is the reference implementation, and `tests/test_truth_forensics_parity.py` holds the browser engine to it byte for byte. See `adr/0003-truth-forensics-static-engine.md`.

## 3. Data model

Result documents are canonical JSON (`sort_keys`, compact separators, `ensure_ascii`), the same encoding RFED uses. They contain no floats: percentages are integers, rounded half-up, and durations are integer milliseconds. That is what makes Python and JavaScript output comparable byte for byte.

| Object | Key fields |
|---|---|
| Case manifest (`clearglass.truth-forensics.case/1`) | `case_id`, `title`, `claim`, `analyst`, `analysis_at`, `demonstration`, `evidence[]` (`evidence_id`, `file`, `label`, `acquired_at`, `acquired_by`, optional `declared_mime`, `object_kind`, `parent_id`, `transformation`, `upstream_source`, `observations`), `channels[]`, `tolerances`, `reviews[]` |
| Evidence record | `evidence_id`, `label`, `source_type`, `object_kind` (ORIGINAL / DERIVATIVE / ANALYSIS_RESULT), `content_sha256`, `size_bytes`, `mime_sniffed`, `mime_declared`, `declared_name`, `acquired_at`, `acquired_by`, `acquisition_method`, `processing_boundary`, `provenance_state`, `parent_id`, `transformation`, `upstream_source`, `demonstration` |
| Ledger record | `seq`, `event`, `subject_id`, `parent_ids`, `actor`, `at`, `detail`, `software`, `prev_hash`, `record_hash` |
| Indicator | `code` (e.g. `TEMPORAL.FRAME_TIMING_ANOMALY`), `category`, `title`, `evidence`, `method`, `confidence`, `limitation`, `alternatives`, `state`, `analyzer`, `location`, `finding_id` (`EV-A#CODE~n`) |
| Result (`clearglass.truth-forensics.result/1`) | `summary`, `evidence`, `analyses`, `indicators`, `correlation`, `claim`, `consistency`, `bifocal`, `timelines`, `graph`, `provenance`, `reviews`, `ai_audit`, `external_ai`, `telemetry`, `job`, `disclaimer` |

Ledger chaining: `record_hash = sha256(prev_hash + canonical_json(body))`, starting from a genesis hash of 64 zeros. Altering any past record breaks every link after it. `python -m truth_forensics verify-ledger` replays a chain.

## 4. Methodology

### 4.1 Evidence status

Every item carries one of VERIFIED, SUPPORTED, INCONCLUSIVE, UNVERIFIED or SIMULATED. Two rules apply:

- **VERIFIED requires a human ACCEPT.** No analyzer output can produce it on its own.
- **Demonstration data is always SIMULATED**, whatever a reviewer decides.

### 4.2 Indicators

The engine reports 25 structural indicator codes across seven categories:

| Category | Codes |
|---|---|
| SPATIAL | `COPY_MOVE` |
| TEMPORAL | `EDIT_LIST`, `FRAME_TIMING_ANOMALY`, `IRREGULAR_INTERVALS`, `TRACK_DURATION_MISMATCH` |
| SYNTHETIC | `GENERATOR_TAG`, `GENERATION_PARAMETERS` |
| AUDIO | `CLIPPING`, `DIGITAL_SILENCE`, `DISCONTINUITY`, `NOISE_FLOOR_SHIFT` |
| METADATA | `DIMENSION_MISMATCH`, `EDITING_SOFTWARE`, `MODIFIED_AFTER_CREATION`, `TIMESTAMP_MISMATCH` |
| CONTAINER | `ANALYZER_FAILED`, `CRC_MISMATCH`, `FRAGMENTED`, `PARSE_ERROR`, `SIZE_MISMATCH`, `TRAILING_DATA`, `TYPE_MISMATCH` |
| PROVENANCE | `C2PA_MANIFEST_PRESENT`, `NO_CAPTURE_METADATA`, `NO_CREATION_TIME` |

Each indicator states:
- what was observed;
- the bytes or values it was observed in;
- the method;
- a confidence (NONE / LOW / MODERATE / HIGH);
- a limitation;
- the alternative explanations a reviewer should rule out.

Each analyzer also lists what it did **not** perform (for example, optical flow and lighting consistency for video). Those lists appear in the report.

### 4.3 Independence groups

Items are merged into one group, using union-find, when any of the following holds:

- they have identical SHA-256 (DUPLICATE_CONTENT);
- they declare the same upstream source (SHARED_UPSTREAM);
- one is a declared derivative of the other (DERIVATIVE_OF);
- their 64-bit difference hashes differ by 10 bits or fewer (NEAR_DUPLICATE_IMAGE). This rule is an inference, and it is labelled as one.

Only groups are counted as corroboration.

### 4.4 Claim verdicts and confidence

A claim is decomposed into propositions:
- the explicit ones: source, subject, time, place and event;
- two implicit ones: provenance and independent corroboration.

Each proposition's verdict comes from the count of groups that agree or conflict (`claims.verdict_from_counts`):

| Agreeing groups | Conflicting groups | Verdict |
|---|---|---|
| 0 | 0 | UNVERIFIED |
| 0 | ≥ 1 | CONTRADICTED |
| ≥ 1 | ≥ 1 | INCONCLUSIVE (corroboration conflict) |
| 1 | 0 | PARTIALLY_SUPPORTED |
| ≥ 2 | 0 | SUPPORTED |

The claim as a whole is a conjunction: any CONTRADICTED proposition makes it CONTRADICTED; otherwise any INCONCLUSIVE proposition makes it INCONCLUSIVE; it is SUPPORTED only if every proposition is SUPPORTED.

Confidence follows `claims.confidence_for`:

| Verdict | Condition | Confidence |
|---|---|---|
| UNVERIFIED | always | NONE |
| SUPPORTED | ≥ 3 groups and no open caveats | HIGH |
| SUPPORTED | otherwise | MODERATE |
| CONTRADICTED | ≥ 2 conflicting groups, no caveats | MODERATE |
| anything else | | LOW |

### 4.5 ClearGlass Bifocal Evidence Verification

Bifocal verification holds the primary media stream against channels that did not come through the same pipeline:
- an independent sensor;
- a reference clock;
- a custody record that fixed the primary's hash earlier.

The score is the share of applicable checks that agree, as an integer percentage. It is reported only when at least two channels are present. A channel in the primary's independence group is excluded. It is always shown with:

> This score is an analytical heuristic and is not proof of authenticity.

Two adapters are implemented: custody-record hash comparison, and structured JSON channel records. The seven others are listed in `bifocal.ADAPTERS` as `implemented: False`:
- camera telemetry;
- RFC 3161 timestamps;
- detached signatures;
- live sensor feeds;
- device attestation;
- C2PA validation;
- secure logging.

### 4.6 Consistency engine

`consistency.py` sets what each independent group says about WHO, WHAT, WHEN, WHERE, HOW, SOURCE and PROVENANCE side by side, and flags every dimension where groups disagree.

### 4.7 Human review

`review.py` appends decisions; it never edits a finding. The actions are ACCEPT, REJECT, ESCALATE, MARK_INCONCLUSIVE, ADD_EVIDENCE, ANNOTATE, COMMENT and REQUEST_SECOND_REVIEW. The review log is hash-chained like the ledger. Two rules are enforced:

- **Separation of duties.** The analyst who ran the case cannot ACCEPT, REJECT or MARK_INCONCLUSIVE it.
- **Second review.** A second-review request blocks finalisation until a reviewer other than the requester and the analyst decides.

The final status is the analysis combined with the review decision.

### 4.8 Report

`report.py` writes 14 sections. Every line is typed OBSERVATION, INTERPRETATION or CONCLUSION.

Engine-authored text passes a language guard (`report.FORBIDDEN`) that refuses certainty phrasing, such as "is fake", "is authentic", "100% accurate", "guaranteed", "infallible" and "detects all". Quoted user text (the claim, reviewer names and notes) is masked from the guard, because a report must be able to quote a claim it does not endorse.

## 5. The demonstration case

`python -m truth_forensics demo --check` confirms the committed files match the deterministic generator. Every item is synthetic and labelled `DEMONSTRATION DATA — NOT REAL EVIDENCE`.

**Claim:** "Video A shows Forklift FL-3 moving Pallet 7 out of Dock 2 at Northwind Demo Depot at 21:43 on 14 March 2026."

**Contents:** 10 items in 7 independence groups, with 13 open findings.

**Before review:** the claim is INCONCLUSIVE, because an edited repost (EV-F) conflicts, and the repost carries a copy-move indicator over the sign it is used to read. The bifocal score is 75, from 4 applicable checks.

**After the suggested reviews** (reviewer-1 REJECTs EV-F; reviewer-2 ACCEPTs the claim): the claim is SUPPORTED, and every item stays SIMULATED.

```bash
python -m truth_forensics case data/truth-forensics/demo-case.json --json
python -m truth_forensics case data/truth-forensics/demo-case.json --report --review-demo
```

## 6. Security

| Threat | Control | Where |
|---|---|---|
| Executing an upload | Files are only read as bytes and parsed. Nothing is executed, imported, rendered as HTML or passed to a shell | all analyzers |
| Trusting filenames or MIME | Type comes from magic bytes; a declared/sniffed mismatch is an indicator; display names are stripped of control characters and paths | `intake.sniff_mime`, `display_name`, `declared_mime_indicator` |
| Path traversal | `safe_open_path` refuses symlinks and anything outside the case root | `intake.py` |
| Oversized input | 512 MiB hash ceiling; parsers see at most 64 MiB (browser: 256 MiB file, 64 MiB analysis) | `intake.py`, console |
| Decompression bombs | PNG decode refuses more than 16 M pixels; text chunks inflate to at most 64 KiB; the browser's DecompressionStream is capped | `image.py`, browser engine |
| Parser exhaustion | BMFF: at most 200 000 boxes, depth 16, 2 M timing entries. WAV: at most 28.8 M frames analysed (600 s at 48 kHz) | `video.py`, `audio.py` |
| Malformed input | Parse errors become `CONTAINER.PARSE_ERROR` / `ANALYZER_FAILED` indicators, never a crash | all analyzers |
| SSRF | URLs are never fetched. `validate_url` requires https on port 443, and refuses credentials, internal names, numeric/hex hosts and non-public addresses. With `resolve=True`, it also checks every resolved address and warns that an adapter must connect to the checked address | `intake.validate_url` |
| XSS | The console writes with `textContent` only; the parity test fails if an HTML sink appears in the console source | console, `test_truth_forensics_parity.py` |
| Cross-origin leakage | Page CSP: `connect-src 'self'`, `worker-src 'self'`, `object-src 'none'`, `form-action 'none'`. The only fetches are the same-origin demonstration files | `blog/truth-forensics.html` |
| Tampered history | Ledger and review log are hash-chained and replayable | `provenance.py`, `review.py` |
| Overclaiming | Language guard and fixed statements for found / not found | `report.py`, `vocab.py` |

The CSP's `connect-src 'self'` also blocks the site-wide Sentinel console's optional control-plane call on this page. No Sentinel API origin is configured anywhere in the repository today. If one is added, it stays blocked here by design: an evidence page should not talk to another origin.

## 7. Privacy

- The console processes files in the browser, in a Web Worker where available. Nothing is uploaded, and there are no analytics calls from the engine or console.
- The console keeps no evidence in `localStorage`, `sessionStorage` or IndexedDB. **Clear session** discards every item, finding and review from memory.
- `external_ai.enabled` is `false` in every result. No external AI provider is configured or called. An adapter would have to be enabled explicitly, and each call recorded in `ai_audit` with input and output hashes.
- Telemetry records the analyzer, stage, outcome, size and duration. It never records content.

## 8. Testing

| Suite | Scope |
|---|---|
| `tests/test_truth_forensics_engine.py` | Analyzers (including the PNG decompression-bomb cap and name sanitising), correlation, claims, bifocal, consistency, review rules, report sections and guard, demo expectations |
| `tests/test_truth_forensics_security.py` | Path traversal, symlinks, size caps, manifest root containment, SSRF-shaped URLs, executables and archives hashed but never parsed, filename never decides type, truncated and corrupted media, contained analyzer crashes, markup carried as data, duplicate or missing evidence ids |
| `tests/test_truth_forensics_parity.py` | Runs the browser engine under Node on the demo corpus and compares result, report and markdown byte for byte, reviewed and unreviewed. Also compares vocab tables, claim decomposition and the URL guard, and bans HTML sinks in the console. Needs `node` |

133 tests pass (`python3 -m pytest tests/test_truth_forensics_*.py -q`). They run inside `pytest tests/`, the first gate of `scripts/ci_local.py`.

A Chromium smoke test covered:
- the demo run;
- the separation-of-duties refusal;
- the reviewed verdict;
- the 14-section report and chain verification in the browser;
- local files: PNG copy-move found, a URL never fetched, no cross-origin requests, and Clear session;
- no horizontal scroll at 390 px;
- zero page errors and zero CSP violations.

It is not committed, because the repository has no browser-test harness for the static site.

## 9. Operating it

```bash
python -m truth_forensics hash FILE...                 # SHA-256, size, sniffed type
python -m truth_forensics analyze FILE                 # one file's indicators
python -m truth_forensics case MANIFEST --json         # full result document
python -m truth_forensics case MANIFEST --report       # 14-section markdown report
python -m truth_forensics verify-ledger LEDGER.jsonl   # replay the hash chain
python -m truth_forensics check-url URL                # SSRF decision and reasons
python -m truth_forensics demo --check                 # demo files match the generator
```

Changing the engine means changing both implementations, then running the parity test. Page changes follow the runbook in `CLAUDE.md` § Internal linking system.

## 10. Limitations

- **Structural analysis only.** There is no trained classifier, and no optical-flow, lighting, face-identity or object-persistence analysis. The reference engine does not decode video frames; the console compares a few sampled frames by difference hash where the browser can decode the file.
- **JPEG pixel analysis runs only in the browser**, which decodes through canvas. The Python reference engine reads JPEG structure and metadata only.
- **C2PA:** presence only. Signature, certificate chain and hash binding are not validated.
- **Metadata is unsigned.** Every metadata-derived time, place or device is an inference about the world.
- **Near-duplicate grouping is perceptual** and can merge two different but similar pictures. It is labelled as an inference for that reason.
- **Claim decomposition is rule-based.** Unusual phrasing can yield fewer propositions. The decomposition is shown in full so a reviewer can see what was tested.
- **No detection-accuracy figures are claimed.** None have been measured.

## 11. Future integrations (not built)

These are the bifocal adapters listed as `implemented: False`:
- C2PA validation;
- RFC 3161 timestamp tokens;
- detached signatures;
- device attestation;
- camera telemetry;
- live sensor feeds;
- append-only logging systems.

A fetch adapter for URL references would also have to connect to the address `validate_url(resolve=True)` checked. Any model-based analyzer must be opt-in and recorded in `ai_audit`.

## 12. Relationship to Truth Fabric (existing, unmodified)

The repository already held a smaller "Truth Fabric" prototype in the root Next.js app:
- `lib/truth-fabric/schema.ts`;
- `app/api/truth-fabric/assess/route.ts`;
- `app/reality-forensics/page.tsx`;
- `tests/truth-fabric.test.ts`;
- `docs/TRUTH_FABRIC_FORENSICS.md`.

It was left unchanged. It is not a base for this system, for two reasons:
- The root Next.js app is "not currently deployed by any registered workflow" (`docs/BASELINE.md`), so its API route never runs in production.
- Its scoring model contradicts the rules above.

Findings, each reproduced with the repository's own `tsx`:

1. **Copies count as independent channels.** `assessIntegrity` returns `{"score":100,"status":"verified"}` for two items with the *same* SHA-256 that declare `independent: true`. Identical bytes are one source. The existing test `dual independent channels produce a high integrity result` asserts exactly this case.
2. **"verified" without a human decision.** The status is `verified` when the score is at least 85 and there is at most one reason. With `humanGateRequired: true`, the one reason is "Human authorization remains required for material conclusions.", so the machine marks the case verified while stating that a human must decide.
3. **A constant term.** `every((e) => e.sha256.length === 64)` is always true after the zod regex, so every case gets +5.
4. **A figure the code cannot produce.** The page shows a fixed "98.7%" integrity score labelled "LIVE DEMO". `assessIntegrity` only produces multiples of 5; the reachable scores are 55, 60, 70, 75, 95 and 100.
5. **Unstyled page.** The page uses Tailwind utility classes, but the root app has no Tailwind dependency or PostCSS configuration, so those classes have no stylesheet. This was not rendered to confirm.

**Proposed fix, for the owner to decide:**
- group by hash before counting channels;
- never return `verified` without a recorded human decision;
- drop the constant term;
- compute or remove the page's figure.

Changing the existing test's expected verdict is a behaviour change to someone else's code, so it is not made here.
