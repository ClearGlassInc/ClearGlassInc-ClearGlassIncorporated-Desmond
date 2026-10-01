# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass Truth Forensics — evidence provenance and media-integrity analysis.

Stdlib only, offline, deterministic. It provides analytical indicators and
provenance analysis. It does not independently establish the truth of
real-world events and does not replace qualified forensic, legal,
investigative or evidentiary review.

Entry points:
    truth_forensics.case.run_case(case, files, reviews=None, claim=None)
    truth_forensics.report.build_report(result) / render_markdown(report)
    python -m truth_forensics --help

Architecture and methodology: docs/TRUTH_FORENSICS.md.
"""
from .vocab import DISCLAIMER, ENGINE_NAME, ENGINE_VERSION

__all__ = ["DISCLAIMER", "ENGINE_NAME", "ENGINE_VERSION"]
