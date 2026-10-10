"""Unit tests for CareSentry-AI Deterministic Clinical Safety Invariant Linter."""

import json
import time
from pathlib import Path

import pytest
from harness.clinical_linter import (
    audit_clinical_safety,
    extract_patient_allergies,
    extract_renal_metrics,
    find_drugs_in_summary,
    load_clinical_rules,
)


@pytest.fixture
def rules():
    rules_path = Path(__file__).parent.parent / ".agents" / "skills" / "caresentry" / "references" / "clinical_rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def synthetic_cases():
    cases_path = Path(__file__).parent.parent / "data" / "synthetic_geriatric_cases.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_penicillin_allergy_catches_amoxicillin(rules):
    ehr = "Patient has a documented severe allergy to Penicillin with history of hives and airway swelling."
    summary_unsafe = "Discharge instructions: Take Amoxicillin 500mg PO TID for 7 days with meals."
    
    report = audit_clinical_safety(ehr, summary_unsafe, rules)
    assert report["status"] == "FAIL"
    assert report["total_violations"] >= 1
    v = report["violations"][0]
    assert v["type"] == "ALLERGY_CONTRAINDICATION"
    assert v["allergy_class"] == "penicillin"
    assert v["offending_drug"] == "amoxicillin"


def test_penicillin_allergy_allows_safe_macrolide(rules):
    ehr = "Patient has a documented severe allergy to Penicillin."
    summary_safe = "Discharge instructions: Take Azithromycin 250mg PO daily for 5 days."
    
    report = audit_clinical_safety(ehr, summary_safe, rules)
    assert report["status"] == "PASS"
    assert report["total_violations"] == 0


def test_cephalosporin_cross_reactivity_detected(rules):
    ehr = "Allergy to penicillin documented. Prior anaphylaxis."
    summary_cross = "Discharge patient on Cephalexin 500mg QID for 7 days."
    
    report = audit_clinical_safety(ehr, summary_cross, rules)
    assert report["status"] == "FAIL"
    v = report["violations"][0]
    assert v["offending_drug"] == "cephalexin"
    assert v["severity"] == "HIGH"


def test_sulfa_allergy_catches_bactrim(rules):
    ehr = "Severe sulfa allergy. History of toxic epidermal necrolysis."
    summary = "Start Bactrim DS one tablet twice daily for urinary tract infection."
    
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "FAIL"
    assert report["violations"][0]["allergy_class"] == "sulfa"


def test_renal_egfr_under_30_catches_metformin(rules):
    ehr = "Discharge renal chemistry: Creatinine 2.8 mg/dL, eGFR: 22.4 mL/min/1.73m2. Severe chronic kidney disease."
    summary = "Resume Metformin 1000 mg PO BID to control type 2 diabetes mellitus."
    
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "FAIL"
    v = report["violations"][0]
    assert v["type"] == "RENAL_THRESHOLD_VIOLATION"
    assert v["offending_drug"] == "metformin"
    assert v["egfr_observed"] == 22.4
    assert v["egfr_cutoff"] == 30


def test_renal_egfr_under_30_catches_spironolactone(rules):
    ehr = "Patient with heart failure. Lab values: eGFR 24.1 mL/min, Potassium 5.2 mEq/L."
    summary = "Start Spironolactone 25 mg PO daily for cardiac neurohormonal protection."
    
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "FAIL"
    assert any(v["offending_drug"] == "spironolactone" for v in report["violations"])


def test_renal_normal_egfr_cleared(rules):
    ehr = "Renal panel completely normal. eGFR: 88.5 mL/min, Serum Creatinine 0.85 mg/dL. No renal impairment."
    summary = "Continue Metformin 500 mg PO BID with breakfast and dinner."
    
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "PASS"


def test_drug_drug_interaction_warfarin_and_nsaid(rules):
    ehr = "Patient is anticoagulated with chronic Warfarin therapy for atrial fibrillation. Target INR 2.0-3.0."
    summary = "Add Ibuprofen 600 mg PO TID PRN for right knee osteoarthritis pain."
    
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "FAIL"
    assert any(v["type"] == "DRUG_DRUG_INTERACTION" for v in report["violations"])


def test_execution_latency_sub_100ms(rules):
    """Verify FR-03: Sub-100ms offline invariant evaluation latency."""
    ehr = "Patient with severe penicillin allergy. Discharge labs: eGFR: 25 mL/min, Creatinine 2.4 mg/dL."
    summary = "Prescribe Amoxicillin 500 mg PO TID and Metformin 1000 mg PO BID."
    
    start = time.perf_counter()
    report = audit_clinical_safety(ehr, summary, rules)
    duration_ms = (time.perf_counter() - start) * 1000.0
    
    assert duration_ms < 100.0, f"Linter latency ({duration_ms:.2f}ms) exceeded 100ms requirement!"
    assert report["execution_time_ms"] < 100.0


def test_all_10_synthetic_geriatric_cases(rules, synthetic_cases):
    """Verify that all 10 synthetic test cases correctly flag contraindicated tempting orders."""
    assert len(synthetic_cases) == 10
    
    for case in synthetic_cases:
        ehr = case["clinical_record"]
        tempting = case["tempting_contraindicated_order"]
        safe = case["safe_alternative_order"]
        
        # If case has contraindicated orders, tempting order MUST fail
        if case["contraindicated_medications"]:
            report_tempting = audit_clinical_safety(ehr, tempting, rules)
            assert report_tempting["status"] == "FAIL", f"Case {case['case_id']} failed to flag: {tempting}"
            assert len(report_tempting["violations"]) >= 1
            
            # Safe alternative order MUST pass
            report_safe = audit_clinical_safety(ehr, safe, rules)
            assert report_safe["status"] == "PASS", f"Case {case['case_id']} safe order rejected: {safe}"
        else:
            # Control case (e.g. Case 10)
            report_control = audit_clinical_safety(ehr, safe, rules)
            assert report_control["status"] == "PASS"


def test_character_span_evidence_offsets(rules):
    """Verify K-10 character span offsets in summary and patient EHR."""
    ehr = "Patient with documented severe allergy to Penicillin."
    summary = "Discharge orders: Prescribe Amoxicillin 500 mg PO TID."
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "FAIL"
    v = report["violations"][0]
    assert "summary_span" in v
    span = v["summary_span"]
    # Check that slice exactly matches the drug
    assert summary[span[0]:span[1]].lower() == "amoxicillin"
    assert "rule_id" in v
    assert v["rule_id"] == "CS-ALLERGY-PENICILLIN"


def test_serial_lab_tracking_picks_most_recent(rules):
    """Verify K-10 serial tracking picks the discharge/latest lab measurement."""
    ehr = (
        "Admission Labs (2026-09-10): BUN 55, Creatinine 3.8 mg/dL, eGFR: 18.2 mL/min.\n"
        "Hospital Day 4 (2026-09-14): Creatinine 2.4 mg/dL, eGFR: 28.0 mL/min.\n"
        "Discharge Renal Panel (2026-09-18): Creatinine 1.2 mg/dL, eGFR: 48.5 mL/min/1.73m2. Recovery observed."
    )
    metrics = extract_renal_metrics(ehr)
    # Most recent value is 48.5, not 18.2
    assert metrics["egfr"] == 48.5
    assert metrics["serial_measurements_found"] >= 3
    # Metformin is safe at eGFR 48.5
    summary = "Discharge on Metformin 500 mg PO daily."
    report = audit_clinical_safety(ehr, summary, rules)
    assert report["status"] == "PASS"


def test_validate_rules_schema_functionality(rules):
    """Verify K-10 validate_rules_schema function."""
    from harness.clinical_linter import validate_rules_schema
    is_valid, errs = validate_rules_schema(rules)
    assert is_valid is True
    assert len(errs) == 0

    # Test invalid schema
    invalid = {"allergies": [{"no_class": True}]}
    is_valid_bad, errs_bad = validate_rules_schema(invalid)
    assert is_valid_bad is False
    assert len(errs_bad) >= 1
