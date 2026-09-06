"""ClearGlass Enterprise Patch & Deploy — governed change control primitives.

Stdlib-only by design so it runs in the leanest CI runner (mirrors the
``governance.py`` / ``daily_loop.py`` convention in ``clearglass-commerce``).
The reusable workflow ``.github/workflows/enterprise-patch-deploy.yml`` invokes
``scripts/patch_deploy/risk_score.py`` directly for triage and gate decisions.
"""

from .risk_score import (
    Change,
    Decision,
    RepoInventory,
    RiskCard,
    change_id,
    classify,
    confidence_gate,
    risk_score,
)

__all__ = [
    "Change",
    "Decision",
    "RepoInventory",
    "RiskCard",
    "change_id",
    "classify",
    "confidence_gate",
    "risk_score",
]
