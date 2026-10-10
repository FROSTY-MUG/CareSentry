"""Contract tests proving Track C adapters properly wrap Track A components."""

import pytest
from caresentry_guard.adapters.a_runner import RunnerAdapter, TelemetryWrapper
from caresentry_guard.adapters.a_probe import ProbeAdapter, ProbeResultWrapper
from caresentry_guard.adapters.a_linter import LinterAdapter, LinterReportWrapper
from caresentry_guard.adapters.a_mitigations import MitigationsAdapter


def test_runner_adapter_contract():
    runner = RunnerAdapter(force_simulation=True)
    assert runner.model_id == "Qwen/Qwen2.5-1.5B-Instruct"
    
    prompt = "Patient has severe penicillin allergy."
    input_ids, tokens = runner.tokenize(prompt)
    assert len(tokens) > 0
    assert input_ids.shape[1] == len(tokens)
    
    tel = runner.forward(prompt=prompt, needle="penicillin")
    assert isinstance(tel, TelemetryWrapper)
    assert tel.seq_len == len(tokens)
    assert tel.num_layers == 28
    assert tel.num_heads == 12
    assert tel.is_simulated is True


def test_probe_adapter_contract():
    runner = RunnerAdapter(force_simulation=True)
    probe = ProbeAdapter(runner_adapter=runner, num_control_spans=20)
    
    prompt = "Clinical record: Severe allergy to Penicillin. Discharge scheduled."
    needle = "Severe allergy to Penicillin"
    res = probe.probe(prompt, needle)
    
    assert isinstance(res, ProbeResultWrapper)
    assert res.target_needle == needle
    assert res.control_spans_count == 20
    assert res.classification in ["SUFFICIENTLY_ATTENDED", "NEUTRAL", "DILUTED"]
    assert isinstance(res.to_dict(), dict)


def test_linter_adapter_contract():
    linter = LinterAdapter()
    
    # Unsafe case
    ehr = "Patient with documented allergy to penicillin."
    unsafe_summary = "Discharge orders: Take Amoxicillin 500 mg PO TID."
    report_unsafe = linter.audit(ehr, unsafe_summary)
    
    assert isinstance(report_unsafe, LinterReportWrapper)
    assert report_unsafe.status == "FAIL"
    assert report_unsafe.total_violations >= 1
    assert any(v["offending_drug"] == "amoxicillin" for v in report_unsafe.violations)
    
    # Safe case
    safe_summary = "Discharge orders: Take Azithromycin 250 mg PO daily."
    report_safe = linter.audit(ehr, safe_summary)
    assert report_safe.status == "PASS"
    assert report_safe.total_violations == 0


def test_mitigations_adapter_contract():
    doc = "Line 1.\nLine 2.\nLine 3."
    constraint = "Penicillin allergy"
    
    pinned = MitigationsAdapter.pin_anchor(doc, constraint)
    assert constraint in pinned
    assert "[CARESENTRY-AI SYSTEM ANCHOR: HARD CLINICAL SAFETY INVARIANT]" in pinned
    
    reordered = MitigationsAdapter.reorder_recency(doc, constraint)
    assert constraint in reordered
    assert "[CRITICAL SAFETY SUMMARY - RECENCY ANCHOR]:" in reordered
