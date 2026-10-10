"""Unit tests for Grounding, Policy State Machine, De-ID, and Patient Pack."""

from caresentry_guard.deid.scrubber import DeidentificationScrubber
from caresentry_guard.grounding.engine import EvidenceGroundingEngine
from caresentry_guard.packs.patient_pack import PatientPackGenerator, calculate_flesch_kincaid
from caresentry_guard.policy.engine import PolicyState, SafetyPolicyEngine


def test_evidence_grounding_flags_hallucination():
    ehr = "Patient with community acquired pneumonia. Allergies: Penicillin anaphylaxis. Labs: eGFR 65 mL/min."
    hallucinated_summary = "Patient discharged. Prescribe Ciprofloxacin 500mg PO daily. Patient underwent emergency surgery."

    engine = EvidenceGroundingEngine()
    rep = engine.audit_grounding(ehr, hallucinated_summary)

    assert rep.total_sentences >= 2
    assert rep.unsupported_count >= 1
    assert rep.safety_critical_violations >= 1


def test_policy_engine_state_transitions():
    policy = SafetyPolicyEngine(max_retry_cycles=3)

    # 1. Clean case -> VERIFIED
    clean_dec = policy.evaluate(
        raw_summary="Take Acetaminophen PRN.",
        linter_status="PASS",
        linter_violations=[],
        injection_detected=False,
        injection_findings=[],
        grounding_score=0.90,
        safety_critical_violations=0,
    )
    assert clean_dec.state == PolicyState.VERIFIED
    assert clean_dec.is_safe_to_release is True

    # 2. Prompt injection -> WITHHELD
    inj_dec = policy.evaluate(
        raw_summary="Summary",
        linter_status="PASS",
        linter_violations=[],
        injection_detected=True,
        injection_findings=["adversarial override"],
        grounding_score=0.90,
        safety_critical_violations=0,
    )
    assert inj_dec.state == PolicyState.WITHHELD
    assert inj_dec.is_safe_to_release is False
    assert inj_dec.escalate_to_human is True

    # 3. Linter failure with retries exhausted -> WITHHELD + Escalate
    fail_dec = policy.evaluate(
        raw_summary="Prescribed Amoxicillin",
        linter_status="FAIL",
        linter_violations=[{"offending_drug": "amoxicillin"}],
        injection_detected=False,
        injection_findings=[],
        grounding_score=0.90,
        safety_critical_violations=0,
        retry_cycle_count=3,
    )
    assert fail_dec.state == PolicyState.WITHHELD
    assert fail_dec.is_safe_to_release is False
    assert fail_dec.escalate_to_human is True

    # 4. Severe attention dilution -> ABSTAIN
    dilute_dec = policy.evaluate(
        raw_summary="Discharge notes",
        linter_status="PASS",
        linter_violations=[],
        injection_detected=False,
        injection_findings=[],
        grounding_score=0.90,
        safety_critical_violations=0,
        z_score=-0.75,
    )
    assert dilute_dec.state == PolicyState.ABSTAIN
    assert dilute_dec.is_safe_to_release is False


def test_deidentification_scrubber():
    scrubber = DeidentificationScrubber()
    phi_sample = (
        "PATIENT: Eleanor Vance, MRN: SYN-88219. Phone: 555-123-4567. "
        "Email: eleanor.vance@example.com. Date: 2026-09-14. SSN: 123-45-6789."
    )
    res = scrubber.scrub(phi_sample)
    assert res.redactions_count >= 5
    assert "Eleanor Vance" not in res.scrubbed_text
    assert "555-123-4567" not in res.scrubbed_text
    assert "eleanor.vance@example.com" not in res.scrubbed_text
    assert "123-45-6789" not in res.scrubbed_text


def test_patient_pack_generation():
    gen = PatientPackGenerator()
    summary = (
        "You are being discharged today following treatment for pneumonia. "
        "Take your medications as directed. Rest and drink fluids."
    )
    pack = gen.generate_pack(summary, patient_name="Eleanor Vance")

    assert pack.flesch_kincaid_grade_level > 0.0
    assert len(pack.teach_back_questions) >= 3
    assert len(pack.daily_medication_schedule) >= 3
    assert "CareSentry Verified Patient Guide" in pack.large_print_html
    assert "एलर्जी" in pack.hindi_translation_summary
