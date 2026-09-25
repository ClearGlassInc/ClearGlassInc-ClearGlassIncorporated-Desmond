# ClearGlass Credit-File Remediation Control

## Purpose

Track consumer credit-file accuracy work as an evidence-controlled process. This repository does **not** change a bureau score and must not claim that a particular score is guaranteed.

## Current reported baseline

Source: user-provided TransUnion Credit Health snapshot dated September 25, 2026.

- Reported score: 595
- Change: -26 points since August
- Reported utilization: 103%
- High-impact factor: high available-credit usage
- Medium-impact factor: 3–4 hard inquiries in the prior 12 months
- No delinquency or derogatory records shown
- No judgments or bankruptcies shown
- Oldest accounts: approximately 5 years
- Report mentions recent Neo and Easy Financial inquiries
- Report mentions a $3 Neo over-limit amount in August
- RBC inquiry reported as removed

## Existing external case references

- TransUnion: V64687
- Neo Financial: 6470836

## Control objectives

1. Preserve the exact bureau snapshot as the baseline.
2. Record each tradeline/inquiry as a separate evidence item.
3. Distinguish **accurate**, **inaccurate**, **unverified**, and **disputed** information.
4. Never request deletion solely because accurate information lowers a score.
5. Never fabricate creditor data, authorization, balances, limits, disputes, or outcomes.
6. Do not expose account numbers or other sensitive financial identifiers in repository content.
7. Require human authorization before external communications or financial actions.
8. Reconcile TransUnion and Equifax independently.

## Evidence schema

Each record should capture:

| Field | Required |
|---|---|
| Bureau | Yes |
| Furnisher / creditor | Yes |
| Account or inquiry reference (redacted) | Yes |
| Item type | Yes |
| Reported date | Yes |
| Balance | When applicable |
| Credit limit | When applicable |
| Utilization | When applicable |
| Inquiry type | When applicable |
| Authorization / permissible purpose status | When applicable |
| Evidence source | Yes |
| Dispute status | Yes |
| Last verified | Yes |
| Correction requested | Yes |
| Correction confirmed | Yes/No |
| Notes | Yes |

## Current remediation queue

### P0 — Neo utilization

Verify the 103% utilization calculation against the underlying balance, credit limit, statement date, and bureau reporting date. If the reported data is inaccurate, pursue correction with the furnisher and bureau.

### P1 — Neo inquiry

Verify inquiry date, hard/soft classification, purpose, and authorization. Remove only if it is inaccurate, unauthorized, improperly reported, or cannot be verified under the applicable process.

### P1 — Easy Financial inquiry

Reconcile the apparent current Easy Financial inquiry against the previously observed removal. Do not assume either state is correct until the current consumer disclosure is verified.

### P2 — RBC inquiry

Confirm that the previously removed inquiry remains absent and that no duplicate remains.

## Operational rule

The target is an accurate and healthier credit profile. A 780 score is an aspiration, not a guaranteed result. Score movement must be measured from future bureau reports rather than promised in advance.
