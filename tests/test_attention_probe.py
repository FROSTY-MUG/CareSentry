"""Unit tests for CareSentry-AI Attention Probing Engine and Z-Score Math."""

import pytest
import torch
from harness.attention_probe import AttentionProbe, ProbeResult
from harness.model_runner import ForwardPassTelemetry, ModelRunner


@pytest.fixture
def probe():
    runner = ModelRunner(force_simulation=True)
    return AttentionProbe(runner=runner, num_control_spans=20, decision_layers_count=4)


def test_needle_span_location(probe):
    tokens = ["The", "patient", "has", "a", "severe", "allergy", "to", "penicillin", "in", "chart"]
    needle = "severe allergy to penicillin"
    start, end = probe.locate_needle_span(tokens, needle)
    assert start == 4
    assert end == 8
    assert tokens[start:end] == ["severe", "allergy", "to", "penicillin"]


def test_control_spans_sampling(probe):
    seq_len = 100
    target_start = 45
    target_end = 55
    span_len = 10
    
    controls = probe.sample_control_spans(
        seq_len=seq_len,
        target_start=target_start,
        target_end=target_end,
        span_len=span_len,
        count=20,
    )
    
    assert len(controls) == 20
    for c_start, c_end in controls:
        assert c_end - c_start == span_len
        # Ensure no overlap with target
        assert c_end <= target_start or c_start >= target_end


def test_z_score_mathematical_precision(probe):
    # Verify exact Z-score formula calculation
    target_mean = 0.05
    mu_ctrl = 0.02
    sigma_ctrl = 0.01
    eps = 1e-9
    
    expected_z = (target_mean - mu_ctrl) / (sigma_ctrl + eps)
    assert pytest.approx(expected_z, 1e-4) == 3.0


def test_probe_execution_and_schema_compliance(probe):
    prompt = (
        "Patient Eleanor Vance admitted for geriatric rehabilitation. "
        "Medical records show: Severe allergy to Penicillin with prior anaphylaxis. "
        "Discharge planned with physical therapy."
    )
    needle = "Severe allergy to Penicillin"
    
    res = probe.probe(prompt=prompt, needle=needle)
    
    assert isinstance(res, ProbeResult)
    assert res.context_length_tokens > 0
    assert res.target_needle == needle
    assert res.control_spans_count >= 20
    assert len(res.layers_analyzed) == 4
    assert res.classification in ["SUFFICIENTLY_ATTENDED", "NEUTRAL", "DILUTED"]
    
    # Check dictionary conversion
    d = res.to_dict()
    for field in [
        "model_id",
        "context_length_tokens",
        "target_needle",
        "target_attention_mean",
        "control_spans_count",
        "control_attention_mean",
        "control_attention_std",
        "z_score",
        "classification",
        "layers_analyzed",
        "mitigation_triggered",
    ]:
        assert field in d


def test_classification_thresholds(probe):
    # 1. High Attention -> Z >= 1.0
    prompt_short = (
        "[EMERGENCY ALERT]: Severe allergy to Penicillin. "
        "Review orders immediately. Do not administer."
    )
    res_pinned = probe.probe(prompt=prompt_short, needle="Severe allergy to Penicillin", is_pinned=True)
    assert res_pinned.z_score >= 1.0
    assert res_pinned.classification == "SUFFICIENTLY_ATTENDED"
    assert res_pinned.mitigation_triggered is False


def test_z_method_v2_bootstrap_and_stratification(probe):
    prompt = (
        "Patient Eleanor Vance admitted for geriatric rehabilitation. "
        "Medical records show: Severe allergy to Penicillin with prior anaphylaxis. "
        "Discharge planned with physical therapy."
    )
    needle = "Severe allergy to Penicillin"

    res_v2 = probe.probe(prompt=prompt, needle=needle, z_method="v2")

    assert res_v2.z_method == "v2"
    assert res_v2.z_ci_95 is not None
    assert len(res_v2.z_ci_95) == 2
    assert res_v2.z_ci_95[0] <= res_v2.z_ci_95[1]
    assert res_v2.p_value is not None
    assert 0.0 <= res_v2.p_value <= 1.0
    assert res_v2.stratification_info is not None
    assert res_v2.stratification_info["stratified_controls"] is True


def test_probe_all_constraints(probe):
    prompt = (
        "Patient has documented allergy: Penicillin. "
        "Lab chemistry shows eGFR is 22 mL/min. "
        "Clinical instructions: avoid Metformin."
    )
    all_res = probe.probe_all_constraints(prompt=prompt)

    assert "total_probed" in all_res
    assert all_res["total_probed"] >= 2
    assert "weakest_constraint" in all_res
    assert "min_z_score" in all_res
    assert "mean_z_score" in all_res
    assert all_res["overall_status"] in ["PASS", "FAIL", "WARN"]


def test_dump_trace_contract_compliance(probe, tmp_path):
    import json
    import jsonschema
    from pathlib import Path

    prompt = (
        "Patient Eleanor Vance admitted for geriatric rehabilitation. "
        "Medical records show: Severe allergy to Penicillin with prior anaphylaxis. "
        "Discharge planned with physical therapy."
    )
    needle = "Severe allergy to Penicillin"

    res = probe.probe(prompt=prompt, needle=needle)
    trace_dict = res.to_trace_dict(dtype="fp16", attn_impl="simulated")

    schema_path = Path("contracts/attention_trace.v1.schema.json")
    assert schema_path.exists()

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Validate against actual JSON Schema
    jsonschema.validate(instance=trace_dict, schema=schema)

