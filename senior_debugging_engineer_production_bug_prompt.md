# Senior Debugging Engineer Production Bug Prompt

Use this prompt when investigating production bugs, broken workflows, failed builds, runtime errors, API failures, frontend defects, backend regressions, GitHub Actions failures, or integration issues.

---

## Prompt

```text
Think like a senior debugging engineer investigating a production bug.

Here is the code:
[paste code]

Here is the error or bug:
[paste error]

Analyze it carefully and step by step.

Return:
• What the code is doing
• What the real problem is
• Why it fails
• Edge cases involved
• Corrected code ready for production
```

---

## Expanded Version

```text
Act as a senior debugging engineer investigating a production defect.

Your job is to analyze the code and failure mode with precision. Do not guess. Separate symptoms from root cause. Identify the smallest safe fix, then provide production-ready corrected code.

Here is the code:
[paste code]

Here is the error, log, failed test, screenshot, or bug description:
[paste error]

Analyze the issue step by step and return the following sections:

1. What the code is doing
   - Explain the intended behavior.
   - Explain the actual control flow.
   - Identify important assumptions in the code.

2. What the real problem is
   - Identify the root cause, not only the visible symptom.
   - Point to the exact line, block, condition, state transition, dependency, or data shape responsible.

3. Why it fails
   - Explain the failure path.
   - Explain why the bug appears under the reported condition.
   - Include any timing, state, async, dependency, environment, permissions, or data-format issues.

4. Edge cases involved
   - Missing values
   - Empty inputs
   - Invalid inputs
   - Race conditions
   - Retry behavior
   - Permission failures
   - Network failures
   - Stale cache or stale branch state
   - Production-only environment differences
   - Security and validation concerns

5. Corrected production-ready code
   - Provide the full corrected code block.
   - Include safe defaults.
   - Include error handling.
   - Preserve existing behavior unless it is unsafe.
   - Avoid unnecessary rewrites.
   - Explain any intentional tradeoffs.

6. Validation checklist
   - Unit tests to add
   - Integration tests to run
   - Manual checks
   - Deployment or rollback considerations

Be direct. If the provided information is incomplete, state exactly what is missing and still provide the strongest likely diagnosis based on the evidence.
```

---

## Best Use Cases

- GitHub Actions failures
- JavaScript runtime errors
- React rendering bugs
- API request failures
- Python exceptions
- Build and deployment errors
- Database query defects
- Authentication or permission failures
- Race conditions
- Regression analysis
- Production incident review

---

## Operator Note

The goal is not just to fix the visible error. The goal is to identify the production-grade root cause, harden the failure path, and ship the smallest safe correction.
