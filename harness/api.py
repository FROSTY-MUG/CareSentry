"""CareSentry-AI Public Stable API Surface (v1.1.0).

This module defines the documented public API for CareSentry-AI.
Tracks B, C, and external integrations should import from `harness.api` or `harness`.
All symbols exposed here are subject to backward-compatibility commitments.
"""

from __future__ import annotations

# Re-export core classes and functions
from harness.attention_probe import AttentionProbe, ProbeResult
from harness.clinical_linter import (
    audit_clinical_safety,
    extract_patient_allergies,
    extract_renal_metrics,
    find_drugs_in_summary,
    load_clinical_rules,
)
from harness.mitigations import (
    MitigationStrategy,
    STRATEGIES,
    apply_anchor_pinning,
    apply_combined_remediation,
    apply_recency_reordering,
    register_strategy,
)
from harness.model_runner import ForwardPassTelemetry, ModelRunner
from harness.self_healer import (
    HealingCycleRecord,
    ReflectionResult,
    SelfHealingLoop,
)
from harness.blockwise_attention import BlockwiseAttentionEstimator
from harness.span_locator import SpanLocator, SpanLocationError
from harness.plugins import PluginManager, MonotonicSafetyViolation, get_plugin_manager

__version__ = "1.1.0"

__all__ = [
    "__version__",
    "AttentionProbe",
    "ProbeResult",
    "ModelRunner",
    "ForwardPassTelemetry",
    "audit_clinical_safety",
    "load_clinical_rules",
    "extract_patient_allergies",
    "extract_renal_metrics",
    "find_drugs_in_summary",
    "apply_anchor_pinning",
    "apply_recency_reordering",
    "apply_combined_remediation",
    "MitigationStrategy",
    "STRATEGIES",
    "register_strategy",
    "SelfHealingLoop",
    "ReflectionResult",
    "HealingCycleRecord",
    "BlockwiseAttentionEstimator",
    "SpanLocator",
    "SpanLocationError",
    "PluginManager",
    "MonotonicSafetyViolation",
    "get_plugin_manager",
]
