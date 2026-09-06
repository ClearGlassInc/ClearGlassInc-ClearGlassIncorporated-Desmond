# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Command-line entry point for the ClearGlassInc Artemis API.

The package-level ``artemis-api`` console script resolves here.  The actual
service implementation used by the deployment artifact lives in
``deployment/artemis/app/main.py``; this wrapper imports that app and starts it
with uvicorn so local package installs and CI smoke tests exercise the same
FastAPI application.
"""
from __future__ import annotations

import os

import uvicorn

from deployment.artemis.app.main import app


def main() -> None:
    """Run the Artemis FastAPI service from the installed console script."""
    host = os.getenv("ARTEMIS_API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("ARTEMIS_API_PORT", "8080")))
    uvicorn.run(app, host=host, port=port)


__all__ = ["app", "main"]
