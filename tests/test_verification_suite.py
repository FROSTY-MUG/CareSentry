"""Verification Test Suite for CareSentry-AI 15 Synthetic Clinical Acceptance Cases.

Implements Verification PRD Section 9 & Acceptance Criteria DEMO-02..05, INN-04:
- Evaluates 15 synthetic clinical test cases covering baseline, allergy, renal, position,
  malformed input, and self-healing exhaustion scenarios.
- Verifies deterministic safety invariant gate independence from attention score.
"""

import json
from pathlib import Path
import pytest

from harness.clinical_linter import audit_clinical_safety
from harness.self_healer import SelfHealingLoop


@pytest.fixture(scope="module")
def verification_cases():
    data_path = Path("data/synthetic_15_verification_cases.json")
    assert data_path.exists(), "synthetic_15_verification_cases.json must exist in data/"
    with open(data_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    assert len(cases) == 15, f"Expected 15 verification cases, found {len(cases)}"
    return cases


def test_all_15_synthetic_cases_deterministic_invariant_gate(verification_cases):
    """Test deterministic invariant gate on all 15 verification cases."""
    results_summary = []

    for case in verification_cases:
        cid = case["case_id"]
        raw_ehr = case["raw_ehr"]
        draft_summary = case["draft_summary"]
        expected_status = case["expected_invariant_status"]
        expected_count = case["expected_violations_count"]

        lint_res = audit_clinical_safety(
            summary_text=draft_summary,
            patient_record_text=raw_ehr,
        )

        assert lint_res["status"] == expected_status, (
            f"Case {cid} ('{case['title']}'): expected {expected_status}, got {lint_res['status']}. "
            f"Violations: {lint_res['violations']}"
        )

        if expected_status == "FAIL":
            assert len(lint_res["violations"]) >= expected_count, (
                f"Case {cid}: expected at least {expected_count} violations, got {len(lint_res['violations'])}"
            )
        else:
            assert len(lint_res["violations"]) == 0, (
                f"Case {cid}: expected 0 violations for PASS, got {len(lint_res['violations'])}"
            )

        results_summary.append({
            "case_id": cid,
            "title": case["title"],
            "status": lint_res["status"],
            "violations": len(lint_res["violations"]),
        })

    assert len(results_summary) == 15


def test_verification_case_15_exhaustion_hold():
    """Verify Case 15: persistent stubborn failure results in WITHHELD status and safety hold."""
    loop = SelfHealingLoop(max_cycles=3, initial_temperature=0.70)
    raw_ehr = "PATIENT: Walter Simmons | ALLERGIES: Anaphylaxis to Penicillin | RENAL: eGFR 18 mL/min."
    bad_summary = "Discharge orders: Prescribe Amoxicillin 500mg PO TID and Metformin 1000mg BID."

    def stubborn_gen(prompt, reflection, temp):
        return bad_summary

    result = loop.run(raw_ehr, bad_summary, generator_callback=stubborn_gen)

    assert result.initial_status == "FAIL"
    assert result.final_status == "WITHHELD"
    assert result.healed is False
    assert result.total_cycles_run == 3
    assert "WITHHELD BY CARESENTRY SAFETY GATE" in result.final_summary
    assert len(result.remaining_violations) >= 2
