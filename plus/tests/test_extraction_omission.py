"""Unit tests for F-04 Structured Extraction and Reverse Omission Checker."""

import pytest
from caresentry_plus.extraction.extractor import StructuredExtractor
from caresentry_plus.extraction.omission_checker import OmissionChecker


@pytest.fixture
def extractor():
    return StructuredExtractor()


@pytest.fixture
def omission_checker():
    return OmissionChecker()


def test_structured_extractor_demographics_and_labs(extractor):
    """Test entity extraction from clinical text."""
    ehr = (
        "Patient is a 68-year-old female weighing 64 kg. "
        "Labs: eGFR 24 mL/min/1.73m2, Creatinine 2.8 mg/dL, Potassium 5.6 mEq/L. "
        "Diagnosed with Chronic Kidney Disease stage 4 and Atrial Fibrillation. "
        "Allergies: Documented Penicillin allergy with anaphylaxis. "
        "Medications: Active order for Eliquis 5 mg BID."
    )
    result = extractor.extract(ehr)
    assert result.patient_age == 68
    assert result.patient_sex == "female"
    assert result.patient_weight_kg == 64.0

    # Labs
    lab_names = {l.name: l for l in result.labs}
    assert "eGFR" in lab_names
    assert lab_names["eGFR"].value == 24.0
    assert lab_names["eGFR"].is_critical is True

    assert "Potassium" in lab_names
    assert lab_names["Potassium"].is_critical is True

    # Allergies
    assert len(result.allergies) >= 1
    assert any("penicillin" in a.allergen.lower() for a in result.allergies)

    # Anticoagulant
    assert any(m.is_anticoagulant for m in result.medications)


def test_reverse_omission_allergy_dropped(omission_checker):
    """F-04: Documented allergy dropped from summary triggers omission."""
    ehr = "DOCUMENTED ALLERGY: Patient has severe Penicillin allergy."
    summary_omitted = "Patient had uneventful stay. Discharged on standard wound care and follow-up."
    
    omissions = omission_checker.check_omissions(ehr, summary_omitted)
    assert any(o.category == "ALLERGY_CONSTRAINT" for o in omissions)

    # When allergy acknowledged, no allergy omission
    summary_preserved = "Discharge instructions: Patient is allergic to Penicillin. Avoid all beta-lactams."
    omissions_clean = omission_checker.check_omissions(ehr, summary_preserved)
    assert not any(o.category == "ALLERGY_CONSTRAINT" for o in omissions_clean)


def test_reverse_omission_renal_impairment_dropped(omission_checker):
    """F-04: Severe renal failure dropped from summary triggers omission."""
    ehr = "Patient with CKD stage 4. Labs show eGFR is 18 mL/min."
    summary_omitted = "Discharge plan: Patient stable. Resume home diet and daily ambulation."

    omissions = omission_checker.check_omissions(ehr, summary_omitted)
    assert any(o.category == "RENAL_PRECAUTION" for o in omissions)

    summary_preserved = "Discharge plan: Patient has renal impairment (eGFR 18). Nephrology follow up arranged."
    omissions_clean = omission_checker.check_omissions(ehr, summary_preserved)
    assert not any(o.category == "RENAL_PRECAUTION" for o in omissions_clean)


def test_reverse_omission_anticoagulant_continuity_dropped(omission_checker):
    """F-04: Active anticoagulant dropped from summary triggers omission."""
    ehr = "Active outpatient medication: Coumadin 5 mg PO daily for stroke prevention."
    summary_omitted = "Discharge orders: Continue previous blood pressure medications."

    omissions = omission_checker.check_omissions(ehr, summary_omitted)
    assert any(o.category == "ANTICOAGULATION_CONTINUITY" for o in omissions)

    summary_preserved = "Discharge orders: Resume Coumadin 5 mg daily; check INR in 3 days."
    omissions_clean = omission_checker.check_omissions(ehr, summary_preserved)
    assert not any(o.category == "ANTICOAGULATION_CONTINUITY" for o in omissions_clean)
