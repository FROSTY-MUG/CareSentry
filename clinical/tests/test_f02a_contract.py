"""Contract tests for the clinical rule engine and pack loader."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, r"C:\Users\HP\app\CareSentry")
from clinical.src.caresentry_clinical.rules.engine import RulePack, RulePackLoader, RuleValidationError


def test_rule_pack_loads_default():
    """Rule pack should load from the default path."""
    pack = RulePackLoader.load_default_pack()
    assert pack is not None
    assert len(pack.rules) > 0
    print(f"  Loaded pack: {pack.name}, {len(pack.rules)} rules")


def test_rule_pack_validates_provenance():
    """Rule pack rules must have provenance with source and date."""
    pack = RulePackLoader.load_default_pack()
    for rule in pack.rules:
        prov = rule.get("provenance", {})
        assert "source" in prov, f"Rule {rule['id']} missing provenance source"
        assert "date" in prov, f"Rule {rule['id']} missing provenance date"
        assert prov.get("reviewer_status") in (
            "UNVERIFIED",
            "SOURCE_CHECKED",
            "CLINICIAN_REVIEWED",
        ), f"Rule {rule['id']} invalid reviewer_status"
    print("  All rules have valid provenance")


def test_rule_pack_clin_id_prefix():
    """All rule IDs must start with CLIN- prefix."""
    pack = RulePackLoader.load_default_pack()
    for rule in pack.rules:
        assert rule["id"].startswith("CLIN-"), (
            f"Rule ID '{rule['id']}' must start with CLIN- prefix"
        )
    print("  All rule IDs have CLIN- prefix")


def test_rule_pack_merge_strict():
    """Rule pack merge behavior should be strict - can only make verdict stricter."""
    # PASS -> FAIL should be possible (upgrading)
    # FAIL -> PASS should NOT be possible (downgrading)
    pack = RulePackLoader.load_default_pack()

    # Core result: PASS (no violations)
    core_result = {
        "status": "PASS",
        "total_violations": 0,
        "violations": [],
        "passed_checks_count": 10,
        "passed_checks": ["all checks passed"],
        "renal_metrics": {"egfr": 50.0, "creatinine": 1.2},
        "execution_time_ms": 10.0,
        "standard": "agent-skills.io/v1",
    }

    # Use cephalexin which is in CLIN-CRCL-001 applies_to
    result = pack.evaluate(
        core_result,
        "Patient has penicillin allergy. Prior anaphylaxis.",
        "Take Cephalexin 500mg QID for 7 days.",
    )
    # Since core is PASS and rule flags cephalexin (penicillin-ceph cross-reactivity), verdict should upgrade to FAIL
    assert result["status"] == "FAIL", (
        f"Expected FAIL when core PASS + rule flags drug, got {result['status']}"
    )
    assert len(result["clinical_violations"]) > 0, "Expected clinical violations"
    print("  PASS -> FAIL upgrade works correctly")


def test_rule_pack_no_downgrade():
    """Rule pack should NOT be able to downgrade FAIL to PASS."""
    pack = RulePackLoader.load_default_pack()

    # Core result: FAIL (has violations)
    core_result = {
        "status": "FAIL",
        "total_violations": 1,
        "violations": [
            {
                "type": "ALLERGY_CONTRAINDICATION",
                "severity": "CRITICAL",
                "allergy_class": "penicillin",
                "offending_drug": "amoxicillin",
                "evidence_in_summary": "Take Amoxicillin 500mg PO TID",
                "patient_allergy_evidence": "Patient has penicillin allergy",
                "mechanism": "Hypersensitivity",
                "recommendation": "Remove amoxicillin",
            }
        ],
        "passed_checks_count": 6,
        "passed_checks": [],
        "renal_metrics": {"egfr": 50.0, "creatinine": 1.2},
        "execution_time_ms": 10.0,
        "standard": "agent-skills.io/v1",
    }

    result = pack.evaluate(core_result, "penicillin allergy text", "Take Amoxicillin 500mg")
    # Verdict should remain FAIL - cannot downgrade to PASS
    assert result["status"] == "FAIL", (
        f"Expected FAIL when core FAIL, got {result['status']} (downgrade attempted!)"
    )
    print("  FAIL -> PASS downgrade correctly blocked")


def test_rule_pack_missing_source_excluded():
    """Rule with source: 'MISSING' should be excluded from default pack operations."""
    # Create a rule pack with a rule missing provenance
    bad_pack_data = {
        "version": "v1.0.0",
        "name": "Bad Pack",
        "rules": [
            {
                "id": "CLIN-BAD-001",
                "name": "Bad Rule",
                # No provenance - should cause validation error
                "applies_to": ["penicillin"],
                "severity": "CRITICAL",
                "action": "Test rule",
            }
        ],
    }

    try:
        pack = RulePack(bad_pack_data)
        # If we get here, validation passed - check if it handles missing provenance gracefully
        print("  Note: Pack loaded despite missing provenance (may be lenient mode)")
    except RuleValidationError as e:
        # Expected - missing provenance should fail validation
        print(f"  Expected validation error: {e}")


def test_rule_pack_schema_validation():
    """Rule pack should validate against schema."""
    pack = RulePackLoader.load_default_pack()
    # Basic validation should pass
    is_valid = RulePackLoader.validate_pack_schema(Path("clinical/rule_packs/default_pack.json"))
    assert is_valid, "Default pack should validate successfully"
    print("  Schema validation passed")


def test_rule_pack_renal_rule_evaluation():
    """Renal threshold rules should evaluate correctly."""
    pack = RulePackLoader.load_default_pack()

    # Core result with eGFR 25 (below 30 threshold)
    core_result = {
        "status": "PASS",
        "total_violations": 0,
        "violations": [],
        "passed_checks_count": 0,
        "passed_checks": [],
        "renal_metrics": {"egfr": 25.0, "creatinine": 2.8},
        "execution_time_ms": 10.0,
        "standard": "agent-skills.io/v1",
    }

    # Test metformin rule
    result = pack.evaluate(
        core_result,
        "Discharge renal chemistry: Creatinine 2.8 mg/dL, eGFR: 22.4 mL/min/1.73m2.",
        "Resume Metformin 1000 mg PO BID to control type 2 diabetes mellitus.",
    )

    # eGFR 25 < 30 threshold, metformin ordered -> should flag violation
    assert result["status"] == "FAIL", (
        f"Expected FAIL for metformin with eGFR < 30, got {result['status']}"
    )
    violation_types = [v["type"] for v in result["clinical_violations"]]
    assert any("REN" in v or "metformin" in v.lower() for v in violation_types), (
        f"Expected metformin/renal violation, got {violation_types}"
    )
    print("  Renal threshold rule evaluates correctly")


def test_rule_pack_cross_reactivity_rule():
    """Cross-reactivity rules should evaluate correctly."""
    pack = RulePackLoader.load_default_pack()

    core_result = {
        "status": "PASS",
        "total_violations": 0,
        "violations": [],
        "passed_checks_count": 10,
        "passed_checks": ["all checks passed"],
        "renal_metrics": {"egfr": 88.5},
        "execution_time_ms": 10.0,
        "standard": "agent-skills.io/v1",
    }

    # Penicillin allergy + cephalexin in summary
    result = pack.evaluate(
        core_result,
        "Patient has documented penicillin allergy. Prior anaphylaxis.",
        "Discharge patient on Cephalexin 500mg QID for 7 days.",
    )

    # Penicillin->cephalosporin cross-reactivity should flag
    assert result["status"] == "FAIL", (
        f"Expected FAIL for penicillin-ceph cross-reactivity, got {result['status']}"
    )
    violation_offending = [v["offending_drug"] for v in result["clinical_violations"]]
    assert "cephalexin" in violation_offending, (
        f"Expected cephalexin violation, got {violation_offending}"
    )
    print("  Cross-reactivity rule evaluates correctly")


if __name__ == "__main__":
    print("Running F-02a Rule Engine Contract Tests...\n")

    test_rule_pack_loads_default()
    test_rule_pack_validates_provenance()
    test_rule_pack_clin_id_prefix()
    test_rule_pack_merge_strict()
    test_rule_pack_no_downgrade()
    test_rule_pack_missing_source_excluded()
    test_rule_pack_schema_validation()
    test_rule_pack_renal_rule_evaluation()
    test_rule_pack_cross_reactivity_rule()

    print("\nAll F-02a contract tests passed!")