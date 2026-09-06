# Deployment Trigger

This file intentionally triggers the `Deploy ClearGlass Agent Live` GitHub Actions workflow through the configured push path for `services/clearglass_agent_service/**`.

Target selected by workflow push default: `fly`.

Dry-run selected by workflow push default: `false`.

Expected behavior:

1. Preflight validates the FastAPI application import.
2. Preflight validates Docker image build.
3. Fly deployment job validates required GitHub secrets.
4. If `FLY_API_TOKEN` and `CLEARGLASS_AGENT_API_KEYS` exist, the workflow deploys to Fly.io.
5. If either secret is missing, the workflow fails with an explicit diagnostic message.

Live health endpoint after successful deployment:

```text
https://clearglass-agent-service.fly.dev/health
```
