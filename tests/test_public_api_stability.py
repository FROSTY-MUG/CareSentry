"""Public API Stability & Backward-Compatibility Test Suite.

Verifies PRD Track A2 Section 2 commitments:
- Preserves all v1.0.0 public classes, functions, and module exports.
- Snapshots public signatures so changes require an explicit versioning decision.
- Confirms `harness.api` facade matches stability guarantees.
"""

import inspect
import pytest
import harness
import harness.api as api
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
from harness.self_healer import (
    SelfHealingLoop,
    ReflectionResult,
    HealingCycleRecord,
)
from harness.clinical_linter import (
    audit_clinical_safety,
    load_clinical_rules,
    extract_patient_allergies,
    extract_renal_metrics,
    find_drugs_in_summary,
)


def test_package_version_bump():
    """Verify semantic version is 1.1.0."""
    assert harness.__version__ == "1.1.0"
    assert api.__version__ == "1.1.0"


def test_model_runner_signature_stability():
    """Verify ModelRunner constructor and forward method signatures."""
    sig_init = inspect.signature(ModelRunner.__init__)
    expected_params = ["self", "model_id", "device", "quantization", "force_simulation"]
    for p in expected_params:
        assert p in sig_init.parameters, f"Missing parameter {p} in ModelRunner.__init__"

    sig_fwd = inspect.signature(ModelRunner.forward)
    assert "prompt" in sig_fwd.parameters
    assert "needle" in sig_fwd.parameters
    assert "is_pinned" in sig_fwd.parameters
    assert "is_recency_reordered" in sig_fwd.parameters


def test_attention_probe_signature_stability():
    """Verify AttentionProbe constructor and probe method signatures."""
    sig_init = inspect.signature(AttentionProbe.__init__)
    for p in ["self", "runner", "model_id", "num_control_spans", "decision_layers_count", "random_seed"]:
        assert p in sig_init.parameters

    sig_probe = inspect.signature(AttentionProbe.probe)
    assert "prompt" in sig_probe.parameters
    assert "needle" in sig_probe.parameters


def test_probe_result_dataclass_fields():
    """Verify ProbeResult maintains all v1.0 fields."""
    v1_fields = [
        "model_id",
        "context_length_tokens",
        "target_needle",
        "target_span_tokens",
        "target_attention_mean",
        "control_spans_count",
        "control_attention_mean",
        "control_attention_std",
        "z_score",
        "classification",
        "layers_analyzed",
        "mitigation_triggered",
        "mitigation_strategy",
        "timestamp",
    ]
    result_inst = ProbeResult(
        model_id="test",
        context_length_tokens=100,
        target_needle="needle",
        target_span_tokens=[10, 15],
        target_attention_mean=0.01,
        control_spans_count=20,
        control_attention_mean=0.01,
        control_attention_std=0.001,
        z_score=1.5,
        classification="SUFFICIENTLY_ATTENDED",
        layers_analyzed=[24, 25, 26, 27],
        mitigation_triggered=False,
    )
    d = result_inst.to_dict()
    for field in v1_fields:
        assert field in d, f"Missing field {field} in ProbeResult output"


def test_mitigations_api_and_registry():
    """Verify mitigation functions and Track B registry (B-0003)."""
    assert callable(apply_anchor_pinning)
    assert callable(apply_recency_reordering)
    assert callable(apply_combined_remediation)
    assert isinstance(STRATEGIES, dict)
    assert "system_anchor_pinning" in STRATEGIES
    assert "recency_reordering" in STRATEGIES

    # Test registration
    def custom_strategy(doc, constraint, **kwargs):
        return doc + "\nCUSTOM"

    register_strategy("custom_test", custom_strategy)
    assert "custom_test" in STRATEGIES
    assert STRATEGIES["custom_test"]("doc", "constraint") == "doc\nCUSTOM"


def test_clinical_linter_signatures_and_output_fields():
    """Verify clinical_linter functions and output field stability."""
    rules = load_clinical_rules()
    res = audit_clinical_safety("Patient has penicillin allergy", "Discharge on amoxicillin", rules)
    
    # Required by contracts/audit_result.v1.schema.json
    assert "status" in res
    assert "total_violations" in res
    assert "violations" in res
    assert "passed_checks_count" in res
    assert "passed_checks" in res
    assert "renal_metrics" in res
    assert "execution_time_ms" in res
    assert "standard" in res


def test_api_facade_parity():
    """Verify harness.api exports all top-level harness symbols."""
    for sym in harness.__all__:
        if sym in ("api", "__version__"):
            continue
        assert hasattr(api, sym), f"Symbol {sym} missing from harness.api"
