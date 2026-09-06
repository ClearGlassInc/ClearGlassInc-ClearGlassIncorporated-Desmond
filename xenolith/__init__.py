# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH — the ClearGlass sovereign intelligence lattice.

A governed, multi-domain command substrate: executive orchestration,
intelligence fusion, cyber defense, threat intelligence, and autonomous agent
collaboration composed into one fail-closed control plane.

The lattice is built from eleven interlocking, independently usable modules:

===================  =====================================================
:mod:`identity`      cryptographic agent identity, signed envelopes, replay
                     protection
:mod:`registry`      the agent civilization — codename, domain, permissions,
                     mission scope, memory partition, health, heartbeat
:mod:`bus`           typed event bus with ordered delivery and dead-lettering
:mod:`policy`        risk scoring, approval gates, escalation, sanitization
:mod:`memory`        partitioned memory fabric with least-privilege reads
:mod:`graph`         entity/relationship store with confidence, provenance,
                     and contradiction tracking
:mod:`telemetry`     hash-chained audit ledger, metrics, anomaly detection
:mod:`fusion`        ingest → correlate → intelligence packets
:mod:`executive`     objectives → policy-constrained missions → ranked tasks
:mod:`lattice`       the composed platform
:mod:`cli`           self-check + operator feed generation
===================  =====================================================

Core invariant, shared with the rest of the ClearGlass estate:

    observe → draft → policy gate → (human approval) → signed execution → audit

Nothing that scores ``high`` or ``critical`` executes without a recorded
approval, and every material step lands in the append-only ledger. The lattice
is **stdlib only** so it runs unchanged in minimal CI environments.
"""
from __future__ import annotations

__version__ = "1.0.0"

__all__ = [
    "Domain",
    "RiskTier",
    "Lattice",
    "LatticeError",
    "PolicyViolation",
]

from .constants import Domain, LatticeError, PolicyViolation, RiskTier
from .lattice import Lattice
