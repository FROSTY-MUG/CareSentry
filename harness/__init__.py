"""CareSentry-AI: Deterministic Attention-Anchored Context Sentry & Invariant Verification Harness."""

from harness.attention_probe import AttentionProbe, ProbeResult
from harness.model_runner import ModelRunner, ForwardPassTelemetry
from harness.mitigations import (
    apply_anchor_pinning,
    apply_recency_reordering,
    apply_combined_remediation,
    MitigationStrategy,
    STRATEGIES,
    register_strategy,
)
from harness.self_healer import SelfHealingLoop, ReflectionResult, HealingCycleRecord
from harness.clinical_linter import (
    audit_clinical_safety,
    load_clinical_rules,
    extract_patient_allergies,
    extract_renal_metrics,
    find_drugs_in_summary,
)
from harness.blockwise_attention import BlockwiseAttentionEstimator
from harness.span_locator import SpanLocator, SpanLocationError
from harness.plugins import PluginManager, MonotonicSafetyViolation, get_plugin_manager
import harness.api as api

__version__ = "1.1.0"

__all__ = [
    "__version__",
    "api",
    "AttentionProbe",
    "ProbeResult",
    "ModelRunner",
    "ForwardPassTelemetry",
    "apply_anchor_pinning",
    "apply_recency_reordering",
    "apply_combined_remediation",
    "MitigationStrategy",
    "STRATEGIES",
    "register_strategy",
    "SelfHealingLoop",
    "ReflectionResult",
    "HealingCycleRecord",
    "audit_clinical_safety",
    "load_clinical_rules",
    "extract_patient_allergies",
    "extract_renal_metrics",
    "find_drugs_in_summary",
    "BlockwiseAttentionEstimator",
    "SpanLocator",
    "SpanLocationError",
    "PluginManager",
    "MonotonicSafetyViolation",
    "get_plugin_manager",
]
