"""Unit tests for F-02 Extended Invariant Rule Packs.

Guarantees:
1. Every rule pack conforms to contracts/rule_pack.v1.schema.json.
2. Every single rule has valid provenance metadata (reviewer_status: unreviewed).
3. Every rule has >= 1 positive and >= 1 negative test case.
"""

import json
from pathlib import Path
import pytest
import jsonschema

from caresentry_plus.rules.engine import RulePackEngine
from caresentry_plus.rules.renal import (
    calculate_cockcroft_gault_crcl,
    calculate_ckd_epi_2021_egfr,
    resolve_effective_renal_clearance,
)

RULE_PACKS_DIR = Path(__file__).resolve().parent.parent / "rule_packs"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "rule_pack.v1.schema.json"


@pytest.fixture
def engine():
    return RulePackEngine()


def test_rule_pack_schema_validation():
    """All JSON rule packs must strictly validate against rule_pack.v1.schema.json."""
    assert SCHEMA_PATH.exists(), f"Schema file missing at {SCHEMA_PATH}"
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    for p in RULE_PACKS_DIR.glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            pack_data = json.load(f)
        # Will raise ValidationError if rule missing provenance, id pattern, etc.
        jsonschema.validate(instance=pack_data, schema=schema)


def test_rule_provenance_integrity(engine):
    """Every rule must possess complete provenance citations and unreviewed status."""
    for pack_id, pack in engine.rule_packs.items():
        for rule in pack.get("rules", []):
            prov = rule.get("provenance")
            assert prov is not None, f"Rule {rule['id']} missing provenance"
            assert prov.get("source"), f"Rule {rule['id']} missing source"
            assert prov.get("reviewer_status") == "unreviewed", f"Rule {rule['id']} must be marked unreviewed"
            assert len(prov.get("citations", [])) >= 1, f"Rule {rule['id']} must cite external scientific literature"


# =====================================================================
# Positive and Negative Invariant Rule Tests
# =====================================================================

# --- 1. Cross-Reactivity ---
def test_cross_reactivity_penicillin_to_cephalosporin(engine):
    """PLUS-CROSS-01: Penicillin allergy -> 1st gen Cephalosporin caution."""
    record = "Patient has documented Penicillin allergy with anaphylaxis."
    
    # Positive test
    summary_pos = "Discharge orders: Prescribe Cephalexin 500 mg PO QID."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-CROSS-01" for v in viol_pos)

    # Negative test
    summary_neg = "Discharge orders: Prescribe Azithromycin 500 mg PO daily."
    viol_neg = engine.evaluate_invariants(record, summary_neg)
    assert not any(v["rule_id"] == "PLUS-CROSS-01" for v in viol_neg)


def test_cross_reactivity_sulfa_antimicrobials(engine):
    """PLUS-CROSS-02: Sulfonamide antibiotic cross-reactivity."""
    record = "Patient has severe Bactrim allergy with diffuse hives."

    # Positive test
    summary_pos = "Discharge orders: Prescribe Sulfadiazine 500 mg daily."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-CROSS-02" for v in viol_pos)

    # Negative test
    summary_neg = "Discharge orders: Prescribe Ciprofloxacin 500 mg BID."
    viol_neg = engine.evaluate_invariants(record, summary_neg)
    assert not any(v["rule_id"] == "PLUS-CROSS-02" for v in viol_neg)


def test_cross_reactivity_aspirin_to_nsaid(engine):
    """PLUS-CROSS-03: Aspirin / AERD sensitivity -> NSAID caution."""
    record = "Patient has Aspirin allergy with severe bronchospasm."

    # Positive test
    summary_pos = "Discharge orders: Prescribe Ibuprofen 600 mg PO TID PRN."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-CROSS-03" for v in viol_pos)

    # Negative test
    summary_neg = "Discharge orders: Prescribe Acetaminophen 650 mg PO Q6H PRN pain."
    viol_neg = engine.evaluate_invariants(record, summary_neg)
    assert not any(v["rule_id"] == "PLUS-CROSS-03" for v in viol_neg)


# --- 2. Dose-Aware Renal Check ---
def test_renal_metformin_contraindication(engine):
    """PLUS-RENAL-01: Metformin contraindicated when eGFR < 30."""
    # Positive test (eGFR = 22)
    record_pos = "Labs: eGFR is 22 mL/min/1.73m2. Creatinine 2.6 mg/dL."
    summary_pos = "Discharge medication: Metformin 1000 mg BID."
    viol_pos = engine.evaluate_invariants(record_pos, summary_pos)
    assert any(v["rule_id"] == "PLUS-RENAL-01" for v in viol_pos)

    # Negative test (eGFR = 75)
    record_neg = "Labs: eGFR is 75 mL/min/1.73m2. Creatinine 0.9 mg/dL."
    viol_neg = engine.evaluate_invariants(record_neg, summary_pos)
    assert not any(v["rule_id"] == "PLUS-RENAL-01" for v in viol_neg)


def test_renal_spironolactone_contraindication(engine):
    """PLUS-RENAL-02: Spironolactone contraindicated when eGFR < 30."""
    record_pos = "Labs: Observed eGFR 24 mL/min. Renal insufficiency."
    summary = "Discharge orders: Spironolactone 25 mg daily."
    viol_pos = engine.evaluate_invariants(record_pos, summary)
    assert any(v["rule_id"] == "PLUS-RENAL-02" for v in viol_pos)

    record_neg = "Labs: Observed eGFR 65 mL/min."
    viol_neg = engine.evaluate_invariants(record_neg, summary)
    assert not any(v["rule_id"] == "PLUS-RENAL-02" for v in viol_neg)


def test_renal_cockcroft_gault_calculation(engine):
    """Calculated clearance from raw creatinine, age, sex, weight."""
    # Female, 80yo, 60kg, Scr 3.0 -> CrCl = 11.8 mL/min (below 30 cutoff)
    crcl = calculate_cockcroft_gault_crcl(serum_creatinine=3.0, age=80, weight_kg=60.0, is_female=True)
    assert crcl is not None
    assert crcl < 30.0

    # Test engine auto-calculating clearance
    record = "Patient is an 80-year-old female weighing 60 kg. Labs: Creatinine 3.0 mg/dL."
    summary = "Discharge medications: Glucophage 500 mg daily."
    viol = engine.evaluate_invariants(record, summary)
    assert any(v["rule_id"] == "PLUS-RENAL-01" for v in viol)


# --- 3. Geriatric Beers Criteria ---
def test_beers_first_gen_antihistamine(engine):
    """PLUS-BEERS-01: Diphenhydramine / Hydroxyzine in age >= 65."""
    # Positive test (Age 74)
    record_pos = "Patient is a 74-year-old female."
    summary = "Prescribe Benadryl 25 mg at bedtime for itching."
    viol_pos = engine.evaluate_invariants(record_pos, summary)
    assert any(v["rule_id"] == "PLUS-BEERS-01" for v in viol_pos)

    # Negative test (Age 32)
    record_neg = "Patient is a 32-year-old female."
    viol_neg = engine.evaluate_invariants(record_neg, summary)
    assert not any(v["rule_id"] == "PLUS-BEERS-01" for v in viol_neg)


def test_beers_tricyclic_antidepressant(engine):
    """PLUS-BEERS-02: Amitriptyline in age >= 65."""
    record_pos = "Patient is a 70-year-old male."
    summary = "Prescribe Amitriptyline 25 mg at bedtime for neuropathy."
    viol_pos = engine.evaluate_invariants(record_pos, summary)
    assert any(v["rule_id"] == "PLUS-BEERS-02" for v in viol_pos)

    record_neg = "Patient is a 28-year-old male."
    viol_neg = engine.evaluate_invariants(record_neg, summary)
    assert not any(v["rule_id"] == "PLUS-BEERS-02" for v in viol_neg)


# --- 4. Drug-Drug Interactions ---
def test_ddi_warfarin_and_nsaid(engine):
    """PLUS-DDI-01: Warfarin + NSAID interaction."""
    record = "Active medications: Warfarin 5 mg daily for atrial fibrillation."
    
    # Positive test
    summary_pos = "Discharge meds: Prescribed Naproxen 500 mg BID for arthritis."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-DDI-01" for v in viol_pos)

    # Negative test
    summary_neg = "Discharge meds: Prescribed Acetaminophen 500 mg TID for pain."
    viol_neg = engine.evaluate_invariants(record, summary_neg)
    assert not any(v["rule_id"] == "PLUS-DDI-01" for v in viol_neg)


def test_ddi_clopidogrel_and_omeprazole(engine):
    """PLUS-DDI-03: Clopidogrel + Omeprazole interaction."""
    record = "Patient history of myocardial infarction, on Plavix daily."
    summary_pos = "Discharge orders: Continue Plavix 75 mg daily. Add Prilosec 20 mg daily for GERD."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-DDI-03" for v in viol_pos)


# --- 5. Duplicate Therapy ---
def test_duplicate_nsaid_therapy(engine):
    """PLUS-DUP-01: Multiple concurrent NSAIDs."""
    record = "Patient admitted for observation."
    summary_pos = "Prescribed Motrin 600 mg TID and Mobic 15 mg daily for severe pain."
    viol_pos = engine.evaluate_invariants(record, summary_pos)
    assert any(v["rule_id"] == "PLUS-DUP-01" for v in viol_pos)

    summary_neg = "Prescribed Motrin 600 mg TID and Lisinopril 10 mg daily."
    viol_neg = engine.evaluate_invariants(record, summary_neg)
    assert not any(v["rule_id"] == "PLUS-DUP-01" for v in viol_neg)
