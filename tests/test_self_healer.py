"""Unit tests for CareSentry-AI Self-Healing Reflection Loop."""

import pytest
from harness.self_healer import SelfHealingLoop


def test_clean_summary_passes_without_healing():
    loop = SelfHealingLoop()
    raw_ehr = "Patient has no known drug allergies. eGFR: 75 mL/min."
    clean_summary = "Discharge instructions: Take Acetaminophen 500mg PO PRN pain."
    
    result = loop.run(raw_ehr, clean_summary)
    assert result.initial_status == "PASS"
    assert result.final_status == "PASS"
    assert result.total_cycles_run == 0
    assert len(result.remaining_violations) == 0


def test_unsafe_summary_heals_via_reflection():
    loop = SelfHealingLoop(initial_temperature=0.70, temperature_step=-0.05)
    raw_ehr = "Patient with documented Severe allergy to Penicillin (anaphylaxis in 2018)."
    unsafe_summary = "Discharge orders: Prescribe Amoxicillin 500mg PO TID for 7 days."
    
    result = loop.run(raw_ehr, unsafe_summary)
    
    assert result.initial_status == "FAIL"
    assert result.final_status == "PASS"
    assert result.healed is True
    assert result.total_cycles_run >= 1
    # Verify temperature decreased
    assert result.final_temperature < 0.70
    assert result.final_temperature == pytest.approx(0.65, 1e-3)
    # Offending drug replaced with safe alternative
    assert "amoxicillin" not in result.final_summary.lower()
    assert len(result.remaining_violations) == 0


def test_reflection_temperature_stepping_and_max_cycles():
    loop = SelfHealingLoop(max_cycles=3, initial_temperature=0.70, temperature_step=-0.05)
    raw_ehr = "Patient has severe penicillin allergy and eGFR is 20 mL/min."
    
    # Callback that refuses to heal to test full 3-cycle exhaustion
    def stubborn_generator(prompt, reflection, temp):
        return "Discharge orders: Still prescribing Amoxicillin and Metformin."
    
    result = loop.run(raw_ehr, "Initial bad summary with Amoxicillin", generator_callback=stubborn_generator)
    
    assert result.initial_status == "FAIL"
    assert result.final_status == "WITHHELD"
    assert "WITHHELD BY CARESENTRY SAFETY GATE" in result.final_summary
    assert result.healed is False
    assert result.total_cycles_run == 3
    # Check temperatures across cycles: 0.70 -> 0.65 -> 0.60 -> 0.55
    assert result.cycles[0].temperature == pytest.approx(0.70, 1e-3)
    assert result.cycles[1].temperature == pytest.approx(0.65, 1e-3)
    assert result.cycles[2].temperature == pytest.approx(0.60, 1e-3)
    assert result.cycles[3].temperature == pytest.approx(0.55, 1e-3)
    assert result.final_temperature == pytest.approx(0.55, 1e-3)
