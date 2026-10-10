"""Adapters for Track A harness components.

Track C code MUST NEVER import from harness directly; all interactions
pass through these defensive adapter interfaces.
"""

from caresentry_guard.adapters.a_runner import RunnerAdapter, TelemetryWrapper
from caresentry_guard.adapters.a_probe import ProbeAdapter, ProbeResultWrapper
from caresentry_guard.adapters.a_linter import LinterAdapter, LinterReportWrapper
from caresentry_guard.adapters.a_mitigations import MitigationsAdapter

__all__ = [
    "RunnerAdapter",
    "TelemetryWrapper",
    "ProbeAdapter",
    "ProbeResultWrapper",
    "LinterAdapter",
    "LinterReportWrapper",
    "MitigationsAdapter",
]
