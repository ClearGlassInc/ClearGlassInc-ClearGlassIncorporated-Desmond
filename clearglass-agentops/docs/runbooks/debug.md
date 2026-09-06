# Debug Runbook

Use these commands from the repository root:

```bash
cd clearglass-agentops
npm run doctor
npm run debug
npm run deploy
```

The bot writes JSON evidence into the `reports` folder. Cloud release remains gated until production secrets and target infrastructure are configured.
