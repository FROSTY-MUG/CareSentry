"""Unit tests for CareSentry-AI Prompt Remediation & Mitigations Engine."""

import pytest
from harness.attention_probe import AttentionProbe
from harness.mitigations import (
    SYSTEM_ANCHOR_FOOTER,
    SYSTEM_ANCHOR_HEADER,
    apply_anchor_pinning,
    apply_combined_remediation,
    apply_recency_reordering,
    extract_and_remove_constraint,
)
from harness.model_runner import ModelRunner


@pytest.fixture
def sample_doc():
    paragraphs = [
        "Paragraph 1: General patient history and intake notes.",
        "Paragraph 2: Physical therapy and nutrition evaluations.",
        "Paragraph 3: NOTE: Patient has documented severe allergy to Penicillin and all beta-lactams.",
        "Paragraph 4: Routine lab chemistries and fluid balance chart.",
        "Paragraph 5: Final discharge instructions and outpatient scheduling.",
    ]
    return "\n\n".join(paragraphs)


def test_anchor_pinning_formatting(sample_doc):
    constraint = "Severe allergy to Penicillin"
    pinned = apply_anchor_pinning(sample_doc, constraint)
    
    assert SYSTEM_ANCHOR_HEADER in pinned
    assert SYSTEM_ANCHOR_FOOTER in pinned
    assert constraint in pinned
    assert sample_doc in pinned
    assert pinned.startswith(SYSTEM_ANCHOR_HEADER)


def test_anchor_pinning_with_custom_system_prompt(sample_doc):
    sys_prompt = "You are an expert geriatric clinical care coordinator."
    constraint = "eGFR: 22 mL/min - strictly withhold Metformin"
    pinned = apply_anchor_pinning(sample_doc, constraint, system_prompt=sys_prompt)
    
    assert pinned.startswith(sys_prompt)
    assert SYSTEM_ANCHOR_HEADER in pinned
    assert constraint in pinned


def test_recency_reordering(sample_doc):
    constraint = "NOTE: Patient has documented severe allergy to Penicillin and all beta-lactams."
    reordered = apply_recency_reordering(sample_doc, constraint, recency_percentile=0.85)
    
    assert "[CRITICAL SAFETY SUMMARY - RECENCY ANCHOR]:" in reordered
    assert constraint in reordered
    # Verify it is positioned before the final discharge paragraph
    anchor_idx = reordered.find("[CRITICAL SAFETY SUMMARY - RECENCY ANCHOR]:")
    para5_idx = reordered.find("Paragraph 5:")
    assert anchor_idx < para5_idx
    assert anchor_idx >= len(sample_doc) * 0.40


def test_combined_remediation(sample_doc):
    constraint = "Severe sulfa allergy"
    combined = apply_combined_remediation(sample_doc, constraint)
    
    assert SYSTEM_ANCHOR_HEADER in combined
    assert "[CRITICAL SAFETY SUMMARY - RECENCY ANCHOR]:" in combined
    assert constraint in combined


def test_mitigation_remedies_attention_dilution():
    runner = ModelRunner(force_simulation=True)
    probe = AttentionProbe(runner=runner)
    
    needle = "Severe allergy to Penicillin"
    doc = (
        "Opening notes. " + ("Middle padding text for geriatric nursing log. " * 80) +
        f"Critical alert: {needle}. " +
        ("Additional lengthy discharge and therapy documentation. " * 80) +
        "Discharge orders."
    )
    
    # Baseline
    res_base = probe.probe(doc, needle, is_pinned=False)
    # Pinned
    doc_pinned = apply_anchor_pinning(doc, needle)
    res_pinned = probe.probe(doc_pinned, needle, is_pinned=True)
    
    assert res_pinned.z_score > res_base.z_score
    assert res_pinned.z_score >= 1.0
    assert res_pinned.classification == "SUFFICIENTLY_ATTENDED"
