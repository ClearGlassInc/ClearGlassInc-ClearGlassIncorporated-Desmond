# PERCIVAL · PFAS — Compliance & Decision Intelligence (Ontario)

> Defensive PFAS intelligence agent inside the **PERCIVAL** control plane.
> Source-of-truth charter for the Phase-One product narrowly described in the
> operator brief. Executable companion: `sentinel/sentinel/pfas.py` +
> `sentinel/tests/test_pfas.py`.

## Mission
Build and operate a serious PFAS business in Burlington focused on **PFAS
screening, compliance analytics, source tracing, and treatment operations
support** for municipalities, property owners, industrial sites, and consultants.

## Commercial anchor
Health Canada's interim drinking-water objective tightened to **30 ng/L for
the sum of 25 PFAS**. The 25-analyte list is implemented in `pfas.HC_25_PFAS`
and the threshold in `pfas.HC_25_PFAS_NGL`.

## Best business model
A **PFAS intelligence + compliance platform** with service wrappers — software
first, services second:
- ingest lab results → normalize analytes → classify against guideline
  thresholds → map likely source categories → generate client-ready reports
- premium human-reviewed consulting and sampling coordination as wrappers

## What we sell (Phase One)
1. PFAS screening coordination
2. Compliance reporting (HC interim objective + Ontario MECP)
3. Source-risk mapping
4. Treatment decision support (GAC / IEX / RO comparison briefs)

Packaged as monthly monitoring, incident response, and capital-planning support.

## Why Burlington
The Burlington/Ontario corridor sits near industrial, transportation, and
municipal infrastructure where water risk, source tracing, and documentation
matter. The local angle is to be the operating system that helps regulated
organizations manage PFAS risk continuously.

## Automation-first system (Phase-One workflow — what `pfas.py` implements)
```
upload report → detect PFAS → score risk → generate compliance package
              → recommend next action
```

### Lab CSV ingester (`sentinel/pfas_ingest.py`)
Long-form CSV is the durable, lossless format every accredited lab can emit.
PDF layouts vary per provider and silent miscoding is the worst failure mode
for a compliance tool, so PDF parsing is intentionally **out of scope** here —
the operator workflow for PDF-only labs is *PDF → vendor CSV export → this
ingester.* The ingester:

- accepts long-form CSV (one row per analyte) with synonym-tolerant headers
  (`analyte / value / units` required; `loq / mdl / qualifier / sample_id /
  site_id / matrix / collected / lab / method` recognized);
- converts µg/L · ppb · ppt to ng/L (and rejects anything it can't safely
  convert);
- treats `<`, `ND`, `U`, `BDL` as below-LOQ;
- fails closed on inconsistent sample-level metadata or non-numeric values.

```python
from sentinel.pfas import ScreeningRequest, screen
from sentinel.pfas_ingest import ingest_csv
sample = ingest_csv(open("lab_export.csv").read())
package = screen(ScreeningRequest(...), sample)
```

A sample CSV ships at [`assets/data/pfas-sample.csv`](../assets/data/pfas-sample.csv).

### Site map view (`sentinel.html`)
SENTINEL ships a **PERCIVAL · PFAS** map layer (button + quick chip + command)
that loads a GeoJSON of monitored sites, color-coded by risk band
(green LOW, amber ELEVATED, red EXCEEDANCE) against the HC 30 ng/L threshold.
The demo dataset is at
[`assets/data/pfas-burlington-demo.geojson`](../assets/data/pfas-burlington-demo.geojson)
and is explicitly illustrative; production clients wire their own GeoJSON
endpoint. The site drawer carries a **Download evidence pack** button that
saves the Markdown + JSON pack client-side (same shape as
`sentinel/pfas_export.py`).

### Evidence-pack exporter (`sentinel/pfas_export.py`)
Renders any `CompliancePackage` as **client-ready Markdown** (top line, risk,
detected analytes, next actions, treatment options, references) and as
**machine-readable JSON** for archival. Denied packages export faithfully
(reasons + audit_ref preserved — no fabrication).

### Text-PDF profile (`sentinel/pfas_pdf.py`)
A stdlib-only PDF profile for **text-based** EPA-Method-533-style lab reports.
Extracts the analyte/result/units/LOQ table, hands the rows to the CSV
ingester so the trust loop is identical. **Fail-closed for any layout it
can't safely parse:** scanned/image PDFs are rejected (no silent OCR),
encrypted PDFs are rejected, and tables without recognized PFAS rows raise
`PDFProfileError` rather than inventing data.
- **Inputs:** `Sample` with `AnalyteResult[]` (ng/L, LOQ-aware), `ScreeningRequest`
  with mandatory `client_id / site_owner_ref / jurisdiction / purpose /
  requester_role` (fail-closed if any missing).
- **Scoring:**
  - `LOW` — sum-of-25 (upper bound) < 0.5 × HC objective (15 ng/L)
  - `ELEVATED` — 15 ≤ sum < 30 ng/L → monthly monitoring + pre-design study
  - `EXCEEDANCE` — sum ≥ 30 ng/L → compliance ticket, source characterization,
    treatment evaluation, 7-day resample
- **LOQ handling:** operator-conservative — values <LOQ count toward the
  *upper-bound* sum (not the lower); both bounds reported.
- **Source hints:** matrix + analyte mix → bucketed categories (AFFF, coatings,
  landfill, wastewater…) — informational, never accusatory.
- **Treatment options:** GAC, ion exchange, RO, interim source isolation.
- **Output:** `CompliancePackage` with `audit_ref`, `next_actions`,
  `resample_after_days`, references.

## Revenue architecture
- Subscription software (monitoring + reporting)
- Paid expert review for high-risk cases
- Project-based source tracing + remediation planning
- Referral / implementation revenue from treatment vendors

## What we do NOT overbuild
No national database, no in-house lab. The product is the narrow workflow above
and the compliance package it produces.

## Positioning
A **PFAS compliance and decision intelligence platform** for Ontario — faster
reporting, better risk visibility, less manual work, clearer next steps for
water, property, and infrastructure stakeholders.

## What PERCIVAL PFAS does **not** do
- Does not identify private individuals or link PFAS findings to people
- Does not run offensive or covert collection
- Does not bypass the SENTINEL fail-closed gate or charter

## References
- Health Canada — *Objective for Canadian drinking water: per- and polyfluoroalkyl
  substances (PFAS)* — interim objective 30 ng/L (sum of 25 PFAS).
- Ontario MECP — *Drinking Water Quality Standards* (PFAS where applicable).
