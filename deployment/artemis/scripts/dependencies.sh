#!/usr/bin/env bash
set -euo pipefail

cat <<'JSON'
{
  "service": "clearglassinc-artemis-router",
  "versions": {
    "python": "3.11.10",
    "fastapi": "0.115.5",
    "uvicorn": "0.32.1",
    "postgresql": "15",
    "redis": "7",
    "kubernetes": "1.30",
    "docker": "27",
    "github_actions_runner": "ubuntu-24.04"
  },
  "external_services": [
    "PostgreSQL (OLTP case + feedback store)",
    "Redis (feature/cache/session state)",
    "Object Store S3-compatible (artifacts + lineage)",
    "Kafka/Redpanda (mission event stream)",
    "OPA policy engine",
    "OpenTelemetry Collector",
    "Prometheus + Grafana",
    "Vault/KMS"
  ],
  "environment_variables": [
    "MODEL_NAME",
    "MODEL_VERSION",
    "ENVIRONMENT",
    "POSTGRES_DSN",
    "REDIS_URL",
    "KAFKA_BROKERS",
    "S3_ENDPOINT",
    "S3_BUCKET",
    "AIP_GATEWAY_URL",
    "OPA_ENDPOINT",
    "OTEL_EXPORTER_OTLP_ENDPOINT"
  ],
  "network_requirements": {
    "ingress": ["443/tcp"],
    "service": ["80/tcp"],
    "container": ["8080/tcp"],
    "egress": ["5432/tcp", "6379/tcp", "9092/tcp", "443/tcp", "4317/tcp", "8181/tcp"]
  }
}
JSON
