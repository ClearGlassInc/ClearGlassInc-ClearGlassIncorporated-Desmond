# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

logger = logging.getLogger("artemis")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

REQ_COUNT = Counter("artemis_requests_total", "Total requests", ["endpoint", "status"])
REQ_LATENCY = Histogram("artemis_request_latency_seconds", "Request latency", ["endpoint"])

MODEL_NAME = os.getenv("MODEL_NAME", "clearglassinc-artemis-router")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "staging")

class InferenceRequest(BaseModel):
    query: str = Field(min_length=1)
    mission_id: str
    operator_id: str

class InferenceResponse(BaseModel):
    model: str
    version: str
    environment: str
    recommendation: str
    confidence: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ClearGlassInc Artemis service", extra={"model": MODEL_NAME, "version": MODEL_VERSION})
    yield
    logger.info("Stopping ClearGlassInc Artemis service")

app = FastAPI(title="ClearGlassInc Artemis Model Service", version=MODEL_VERSION, lifespan=lifespan)

@app.get("/health/live")
def health_live():
    return {"status": "live", "ts": int(time.time())}

@app.get("/health/ready")
def health_ready():
    required_env = ["MODEL_NAME", "MODEL_VERSION", "ENVIRONMENT", "POSTGRES_DSN", "REDIS_URL"]
    missing = [v for v in required_env if not os.getenv(v)]
    if missing:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "missing": missing})
    return {"status": "ready"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/v1/infer", response_model=InferenceResponse)
def infer(req: InferenceRequest):
    start = time.time()
    try:
        recommendation = f"Investigate entity graph for mission={req.mission_id}; prioritize corroboration."
        confidence = 0.83
        REQ_COUNT.labels(endpoint="/v1/infer", status="200").inc()
        return InferenceResponse(
            model=MODEL_NAME,
            version=MODEL_VERSION,
            environment=ENVIRONMENT,
            recommendation=recommendation,
            confidence=confidence,
        )
    except Exception as e:
        REQ_COUNT.labels(endpoint="/v1/infer", status="500").inc()
        logger.exception("Inference failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQ_LATENCY.labels(endpoint="/v1/infer").observe(time.time() - start)
