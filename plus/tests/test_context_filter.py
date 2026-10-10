"""Unit tests for F-03 Negation and Context Filter."""

import pytest
from caresentry_plus.rules.context_filter import (
    AllergySeverity,
    AssertionStatus,
    ContextFilter,
)
from caresentry_plus.rules.eval_context_filter import evaluate_context_filter


@pytest.fixture
def filter_engine():
    return ContextFilter()


def test_negation_detection(filter_engine):
    """Test explicit negation phrases."""
    sentences = [
        ("Patient has no known drug allergies (NKDA).", "penicillin"),
        ("Denies any allergy to amoxicillin or other beta-lactams.", "amoxicillin"),
        ("Penicillin allergy was ruled out after skin test.", "penicillin"),
        ("Negative for allergy to sulfa medications.", "sulfa"),
    ]
    for text, entity in sentences:
        assertion = filter_engine.analyze_assertion(text, entity)
        assert assertion.status == AssertionStatus.NEGATED
        assert assertion.is_active_risk is False


def test_historical_tolerance(filter_engine):
    """Test historical tolerance mentions."""
    text = "Patient tolerated amoxicillin in 2019 without any adverse reaction."
    assertion = filter_engine.analyze_assertion(text, "amoxicillin")
    assert assertion.status == AssertionStatus.HISTORICAL
    assert assertion.is_active_risk is False


def test_family_history_attribution(filter_engine):
    """Test family history attribution."""
    text = "Patient's mother has severe penicillin allergy with anaphylaxis."
    assertion = filter_engine.analyze_assertion(text, "penicillin")
    assert assertion.status == AssertionStatus.FAMILY_HISTORY
    assert assertion.is_active_risk is False


def test_ambiguity_fail_safe_behavior(filter_engine):
    """F-03 Invariant: Ambiguous assertions MUST fail safe (marked active risk)."""
    text = "Patient reports possible mild reaction to penicillin decades ago."
    assertion = filter_engine.analyze_assertion(text, "penicillin")
    assert assertion.status == AssertionStatus.AMBIGUOUS
    assert assertion.is_active_risk is True  # FAIL SAFE


def test_allergy_severity_detection(filter_engine):
    """Test anaphylaxis vs mild categorization."""
    text_anaph = "Patient has severe allergy to penicillin causing anaphylaxis and throat closing."
    res_anaph = filter_engine.analyze_assertion(text_anaph, "penicillin")
    assert res_anaph.severity == AllergySeverity.ANAPHYLAXIS

    text_mild = "Patient had mild rash after taking amoxicillin."
    res_mild = filter_engine.analyze_assertion(text_mild, "amoxicillin")
    assert res_mild.severity == AllergySeverity.MILD_OR_INTOLERANCE


def test_labeled_dataset_evaluation_benchmark():
    """F-03 Acceptance: Evaluate labeled set >= 60 sentences with 100% fail-safe guarantee."""
    metrics = evaluate_context_filter()
    assert metrics["total_samples"] >= 60
    assert metrics["status_accuracy"] >= 0.85
    assert metrics["safety_violations_count"] == 0, "Safety invariant failed: active risk was suppressed!"
    assert metrics["fail_safe_guarantee"] is True
