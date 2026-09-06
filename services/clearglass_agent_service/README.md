# ClearGlass Agent Service

ClearGlassInc-only lawful risk-intelligence API service.

This service implements a private control plane for structured public-source and authorized defensive risk analysis. It is designed to support ClearGlass internal agents, executive risk briefings, source audit workflows, and blue-team command surfaces.

The service is limited to lawful public-source and authorized defensive enterprise security workflows.

---

## Files

```text
services/clearglass_agent_service/
  main.py
  agent.py
  schemas.py
  security.py
  requirements.txt
  Dockerfile
```

---

## Environment

Required:

```bash
export CLEARGLASS_AGENT_API_KEYS="change-this-long-random-key"
```

Optional:

```bash
export CLEARGLASS_ALLOWED_ORGS="ClearGlassInc"
export CLEARGLASS_ALLOWED_ORIGINS="https://www.clearglassinc.com"
export CLEARGLASS_AGENT_VERSION="0.1.0"
export PORT=8080
```

---

## Local Run

```bash
cd services/clearglass_agent_service
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ../..
uvicorn services.clearglass_agent_service.main:app --reload --host 127.0.0.1 --port 8080
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Policy check:

```bash
curl http://127.0.0.1:8080/policy \
  -H "X-ClearGlass-Org: ClearGlassInc" \
  -H "X-ClearGlass-API-Key: change-this-long-random-key"
```

Signal packet:

```bash
curl -X POST http://127.0.0.1:8080/v1/signal \
  -H "Content-Type: application/json" \
  -H "X-ClearGlass-Org: ClearGlassInc" \
  -H "X-ClearGlass-API-Key: change-this-long-random-key" \
  -d '{
    "target": "ClearGlass vendor exposure review",
    "mission": "risk_brief",
    "domain": "vendor",
    "constraints": {
      "sources": ["public_web", "vendor_advisory", "news"],
      "time_window": "past_30_days",
      "jurisdiction": "US",
      "max_results": 10,
      "lawful_basis": "public-source enterprise risk analysis"
    }
  }'
```

---

## Docker Run

```bash
docker build -f services/clearglass_agent_service/Dockerfile -t clearglass-agent-service .
docker run --rm -p 8080:8080 \
  -e CLEARGLASS_AGENT_API_KEYS="change-this-long-random-key" \
  clearglass-agent-service
```

---

## Deployment

This is a containerized FastAPI service. Deploy it to any platform that accepts Docker containers:

- Render
- Fly.io
- Railway
- DigitalOcean App Platform
- AWS ECS / App Runner
- Google Cloud Run
- Azure Container Apps

Minimum production controls:

- Rotate `CLEARGLASS_AGENT_API_KEYS`
- Put the service behind HTTPS
- Add gateway-level rate limiting
- Restrict allowed origins
- Use API gateway or SSO JWT validation
- Add structured logs
- Add persistent audit storage
- Add external source connectors only after source terms and lawful basis are reviewed

---

## API Shape

### `GET /health`

Unauthenticated service health.

### `GET /policy`

Authenticated ClearGlass-only policy disclosure.

### `POST /v1/signal`

Authenticated structured signal packet analysis.

Returns an audit-ready `AgentReport` with executive summary, findings, evidence metadata, compliance note, and request audit context.
