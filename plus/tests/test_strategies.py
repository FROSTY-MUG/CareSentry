"""Unit tests for F-17 Mitigation Strategies (Contract C-06)."""

import pytest
from caresentry_plus.strategies.mitigations_plus import (
    PLUS_STRATEGIES,
    PromptParts,
    constraint_repetition_strategy,
    retrieval_then_summarize_strategy,
    safety_pass_map_reduce_strategy,
)


@pytest.fixture
def sample_parts():
    return PromptParts(
        system_prompt="You are a clinical discharge assistant.",
        patient_record=(
            "Patient is an 80yo female. "
            "CRITICAL ALLERGY: Documented anaphylaxis to Penicillin. "
            "Labs: Normal kidney panel."
        ),
        target_constraint="ALLERGY: Penicillin -> Anaphylaxis",
        instruction="Generate discharge instructions.",
        metadata={"case_id": "test_001"},
    )


def test_pure_function_properties(sample_parts):
    """Contract C-06: Strategies must be pure functions with frozen immutability."""
    # Attempting mutation on frozen PromptParts should raise FrozenInstanceError
    with pytest.raises(Exception):
        sample_parts.instruction = "Mutated"

    # Idempotence: calling multiple times on identical input yields identical output
    out1 = constraint_repetition_strategy(sample_parts)
    out2 = constraint_repetition_strategy(sample_parts)
    assert out1 == out2


def test_constraint_repetition_strategy(sample_parts):
    """Test start and end pinning."""
    res = constraint_repetition_strategy(sample_parts)
    assert sample_parts.target_constraint in res.system_prompt
    assert sample_parts.target_constraint in res.instruction


def test_retrieval_then_summarize_strategy(sample_parts):
    """Test constraint retrieval block isolation."""
    res = retrieval_then_summarize_strategy(sample_parts)
    assert "[RELEVANT CRITICAL EVIDENCE BLOCK]" in res.patient_record
    assert "anaphylaxis to Penicillin" in res.patient_record


def test_safety_pass_map_reduce_strategy(sample_parts):
    """Test two-stage prompt structuring."""
    res = safety_pass_map_reduce_strategy(sample_parts)
    assert "Step 1 (Safety Verification Pass)" in res.instruction
    assert "Step 2 (Safe Synthesis Pass)" in res.instruction


def test_strategy_registry_completeness():
    """Verify registry dictionary keys."""
    assert "constraint_repetition" in PLUS_STRATEGIES
    assert "retrieval_then_summarize" in PLUS_STRATEGIES
    assert "safety_pass_map_reduce" in PLUS_STRATEGIES
