# ClearGlass AI Runtime v0.2

## Capabilities
- OpenAI API orchestration
- Multi-agent execution chain
- Persistent JSONL memory
- Telegram alerts
- Slack alerts
- Daily scheduler mode
- Reusable operational runtime

## Agent Chain
1. Intake Agent
2. Planner Agent
3. Executor Agent
4. Auditor Agent
5. Logger Agent

## Installation

```bash
pip install -r requirements.txt
```

Copy environment template:

```bash
cp .env.example .env
```

Set secrets inside `.env`.

---

## Run One Task

```bash
python clearglass_agent_runtime.py --task "Build tomorrow revenue strategy"
```

---

## Run Continuous Scheduler

```bash
python clearglass_agent_runtime.py --schedule --interval-minutes 1440
```

---

## Telegram Setup
1. Create Telegram bot using BotFather.
2. Copy bot token.
3. Get your chat ID.
4. Fill `.env`.

---

## Slack Setup
1. Create Incoming Webhook.
2. Paste webhook URL into `.env`.

---

## Current State
v0.2 is an operational orchestration runtime.

Not yet implemented:
- Vector database memory
- Autonomous browser agents
- Multi-model routing
- Redis/RabbitMQ queues
- Docker deployment
- Kubernetes scaling
- Web dashboard
- Human approval gates

## Strategic Next Evolution
v0.3:
- LangGraph orchestration
- pgvector memory
- Redis queue
- FastAPI control plane
- Docker deployment
- Autonomous task retries
- Browser-use agents
- Revenue analytics engine
