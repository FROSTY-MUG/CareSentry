"""Contract tests for the clinical lane adapter (a_linter.py)."""

import json
import tempfile
import sys
import os

sys.path.insert(0, r"C:\Users\HP\app\CareSentry\clinical")
from adapters.a_linter import audit, normalize_output


def test_audit_returns_known_keys():
    """Audit should return a dict with only known keys (unknown fields dropped)."""
    records = "Patient has penicillin allergy. eGFR 25."
    summary = '{"summary": "Take Amoxicillin 500mg PO TID"}'

    data = audit(records, summary)
    assert "status" in data
    assert "total_violations" in data
    assert "violations" in data
    assert "passed_checks_count" in data
    assert "passed_checks" in data
    assert "renal_metrics" in data
    assert "execution_time_ms" in data
    assert "standard" in data

    # normalize_output should filter to known keys only
    norm = normalize_output(data)
    for key in norm:
        assert key in {
            "status",
            "total_violations",
            "violations",
            "passed_checks_count",
            "passed_checks",
            "renal_metrics",
            "execution_time_ms",
            "standard",
        }, f"Unexpected key: {key}"


def test_normalize_output_drops_unknown():
    """normalize_output should drop any key not in the known set."""
    raw = {
        "status": "FAIL",
        "total_violations": 1,
        "violations": [],
        "passed_checks_count": 0,
        "passed_checks": [],
        "renal_metrics": {"egfr": 25.0, "creatinine": None},
        "execution_time_ms": 10.0,
        "standard": "agent-skills.io/v1",
        "unknown_field_1": "should be dropped",
        "unknown_field_2": 42,
    }
    norm = normalize_output(raw)
    assert "unknown_field_1" not in norm
    assert "unknown_field_2" not in norm
    assert norm["status"] == "FAIL"


def test_audit_with_penicillin_allergy():
    """Penicillin allergy should be detected when contraindicated drug is in summary."""
    records = "Patient has documented penicillin allergy."
    summary = '{"summary": "Take Amoxicillin 500mg PO TID"}'

    data = audit(records, summary)
    assert data["status"] == "FAIL"
    assert data["total_violations"] >= 1

    # Check the violation structure
    violations = data["violations"]
    assert any(v["type"] == "ALLERGY_CONTRAINDICATION" for v in violations)
    assert any(v["allergy_class"] == "penicillin" for v in violations)


def test_audit_safe_summary_passes():
    """A safe summary (no contraindicated drugs) should produce PASS."""
    records = "Patient has penicillin allergy. No other issues."
    summary = '{"summary": "Take Azithromycin 250mg PO daily for 5 days."}'

    data = audit(records, summary)
    assert data["status"] == "PASS"
    assert data["total_violations"] == 0


def test_audit_renal_metrics_present():
    """Renal metrics should be present in the output."""
    records = "Patient eGFR 25 mL/min. Creatinine 2.4 mg/dL."
    summary = '{"summary": "Continue Metformin 500mg PO BID"}'

    data = audit(records, summary)
    assert "renal_metrics" in data
    egfr = data["renal_metrics"].get("egfr")
    assert egfr is not None
    assert egfr == 25.0