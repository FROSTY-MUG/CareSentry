"""Tests for K-03 Robust Span Locator Engine."""

import pytest
from harness.span_locator import (
    SpanLocator,
    SpanLocationError,
    clean_subword_token,
    normalize_text_for_matching,
)


def test_span_locator_exact_words():
    locator = SpanLocator()
    tokens = ["The", "patient", "has", "a", "severe", "allergy", "to", "penicillin", "in", "chart"]
    needle = "severe allergy to penicillin"

    matches = locator.locate(tokens, needle)
    assert len(matches) == 1
    m = matches[0]
    assert m.start_token == 4
    assert m.end_token == 8
    assert tokens[m.start_token:m.end_token] == ["severe", "allergy", "to", "penicillin"]


def test_span_locator_normalized_fuzzy():
    locator = SpanLocator()
    tokens = ["Medical", "history", "shows", "e", "GFR", "is", "18", "mL", "min"]
    needle = "eGFR is 18 mL/min"

    matches = locator.locate(tokens, needle)
    assert len(matches) >= 1
    m = matches[0]
    assert m.start_token >= 3
    assert m.end_token <= 9


def test_span_locator_missing_needle_raises_error():
    locator = SpanLocator()
    tokens = ["Patient", "was", "admitted", "for", "elective", "hip", "replacement"]
    needle = "severe penicillin allergy"

    with pytest.raises(SpanLocationError, match="could not be located"):
        locator.locate(tokens, needle)


def test_span_locator_empty_needle_raises_error():
    locator = SpanLocator()
    tokens = ["Some", "tokens"]
    with pytest.raises(SpanLocationError, match="empty needle"):
        locator.locate(tokens, "")
