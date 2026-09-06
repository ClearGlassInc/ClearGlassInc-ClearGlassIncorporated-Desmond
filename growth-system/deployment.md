# Deployment

The growth-system increment is static-site and Python-test compatible. The command center can be served from GitHub Pages as `/apps/command-center/` when linked. Production integrations for CRM, ad platforms, email providers, analytics, or Palantir must be configured through environment-separated secrets and approval-gated service accounts.

## Local commands

```bash
python -m pytest tests/test_burlington_growth_engine.py -q
python -m http.server 8080
```

Open `http://localhost:8080/apps/command-center/index.html` for the static command center.
