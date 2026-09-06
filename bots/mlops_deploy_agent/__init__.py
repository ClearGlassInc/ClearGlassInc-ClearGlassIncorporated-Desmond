# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""MLOps deploy agent: deterministic, supervisor-orchestrated deployment pipeline.

Compiles a typed DeployPlan into staged execution across registry, runtime,
secrets, and CI adapters with policy gates, repair, rollback, and signed audit.
"""

from .schema import DeployPlan, ModelRef, Target, Policy, StageResult, AuditManifest
from .supervisor import Supervisor, StageFailure, SUPERVISOR_STAGES
from .adapters import (
    RegistryAdapter,
    RuntimeAdapter,
    SecretsAdapter,
    CIAdapter,
    InMemoryRegistry,
    InMemoryRuntime,
    InMemorySecrets,
    InMemoryCI,
)
from .policy import PolicyEngine, PolicyViolation
from .validator import StageValidators

__all__ = [
    "DeployPlan",
    "ModelRef",
    "Target",
    "Policy",
    "StageResult",
    "AuditManifest",
    "Supervisor",
    "StageFailure",
    "SUPERVISOR_STAGES",
    "RegistryAdapter",
    "RuntimeAdapter",
    "SecretsAdapter",
    "CIAdapter",
    "InMemoryRegistry",
    "InMemoryRuntime",
    "InMemorySecrets",
    "InMemoryCI",
    "PolicyEngine",
    "PolicyViolation",
    "StageValidators",
]
