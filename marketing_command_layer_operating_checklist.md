# ClearGlassInc Marketing Command Layer - Weekly Operating Checklist

## Monday (Strategy Reset)
- Confirm weekly campaign objective and primary audience.
- Validate content pillar rotation for cybersecurity, AI infrastructure, and digital authority.
- Review prior week's `marketing/reports/weekly_recap.md` and `campaign_metrics.jsonl`.

## Daily (Execution Cadence)
- Verify daily workflow run completed successfully.
- Check that stage labels progressed: `stage:idea` -> `stage:draft` -> `stage:review` -> `stage:scheduled` -> `stage:published`.
- Confirm platform outputs exist for LinkedIn, Threads, X, email, and website.
- Review quality-gate failures and rerun with `workflow_dispatch` if needed.

## Wednesday (Midweek Tuning)
- Inspect campaign metrics trendline.
- Tighten weak prompts and adjust campaign label taxonomy.
- Triage stale issues and close low-signal work items.

## Friday (Executive Readout)
- Publish weekly recap with outcomes, experiments, and next-step hypotheses.
- Audit failed runs and summarize root-cause themes.
- Archive high-performing content for repurposing backlog.

## Failure Protocol
- If validation fails, block publish-stage transitions.
- If issue/project automation fails, open incident issue with run URL and error logs.
- If metric logging fails, halt optimization decisions until telemetry is restored.
