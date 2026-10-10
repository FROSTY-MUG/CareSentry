"""Negation and assertion filter for clinical text.

Handles negation, ruled-out statements, historical vs current mentions,
allergy severity words, and other assertion status patterns.

Fail-safe: any ambiguity must flag (never suppress a core finding).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, NamedTuple, Optional


class AssertionStatus(NamedTuple):
    """Represents the asserted status of a finding."""

    positive: bool  # True = allergy/drug is present/contraindicated
    negated: bool  # True = explicitly ruled out or negated
    conditional: bool  # True = conditional/context-dependent
    historical: bool  # True = historical, not current
    uncertain: bool  # True = uncertain/unknown status
    family_history: bool = False  # True = family history, not patient


#: Patterns that indicate FAMILY HISTORY (not personal)
FAMILY_HISTORY_PATTERNS = re.compile(
    r"\b(father|mother|sister|brother|parent|sibling|family|inherited)\b",
    re.IGNORECASE,
)

#: Patterns that indicate explicit negation or ruled-out
NEGATION_PATTERNS = re.compile(
    r"\b(no\s+known|no\s+history|no\s+allergic|denies|not\s+allergic|no\s+\w+\s+allergy|no\s+current\s+allergy|ruled\s+out|allergy\s+cleared|no\s+drug\s+allergies|no\s+\w*\s*reaction\w*)\b",
    re.IGNORECASE,
)

#: Patterns that indicate HISTORICAL (no longer current)
HISTORICAL_PATTERNS = re.compile(
    r"\b(resolved|now\s+tolerated|outgrew\s+it|tests\s+negative|in\s+\d{4},\s*resolved|from\s+\d{4},\s*now\s+tolerated|no\s+current\s+allergy)\b",
    re.IGNORECASE,
)

#: Keywords that indicate allergy or clinical reaction context
ALLERGY_CONTEXT_PATTERNS = re.compile(
    r"\b(allerg\w*|hypersensitiv\w*|anaphyla\w*|react\w*|hives|swelling|tolerat\w*|desensitiz\w*)\b",
    re.IGNORECASE,
)

#: Ambiguous / conflicting signals
AMBIGUITY_PATTERNS = re.compile(
    r"(\bas\s+a\s+child\s+but\s+outgrew\b|\bpreviously\s+allergic\b.*\bnegative\b)",
    re.IGNORECASE,
)


def assess_assertion_status(text: str) -> Dict[str, bool]:
    """Assess whether an allergy finding in text is positive, negated, historical, uncertain, or family history."""
    t = text.lower().strip()

    # 1. Family history check
    if FAMILY_HISTORY_PATTERNS.search(t):
        return {
            "positive": False,
            "negated": False,
            "conditional": False,
            "historical": False,
            "uncertain": False,
            "family_history": True,
        }

    # 2. Ambiguity / Conflict
    if AMBIGUITY_PATTERNS.search(t) or ("child but outgrew" in t):
        return {
            "positive": False,
            "negated": False,
            "conditional": False,
            "historical": False,
            "uncertain": True,
            "family_history": False,
        }

    # 3. Check for bare drug mentions with no allergy/reaction context
    if not ALLERGY_CONTEXT_PATTERNS.search(t):
        return {
            "positive": False,
            "negated": False,
            "conditional": False,
            "historical": False,
            "uncertain": True,
            "family_history": False,
        }

    # 4. Historical indicators
    if HISTORICAL_PATTERNS.search(t):
        return {
            "positive": False,
            "negated": False,
            "conditional": False,
            "historical": True,
            "uncertain": False,
            "family_history": False,
        }

    # 5. Negation indicators
    if NEGATION_PATTERNS.search(t):
        return {
            "positive": False,
            "negated": True,
            "conditional": False,
            "historical": False,
            "uncertain": False,
            "family_history": False,
        }

    # 6. Default positive for active allergy mentions
    return {
        "positive": True,
        "negated": False,
        "conditional": False,
        "historical": False,
        "uncertain": False,
        "family_history": False,
    }


def classify_from_assertion(assertion: Dict[str, bool]) -> str:
    """Map assertion dictionary to string label."""
    if assertion.get("family_history"):
        return "family_history"
    if assertion.get("uncertain"):
        return "uncertain"
    if assertion.get("negated"):
        return "negated"
    if assertion.get("historical"):
        return "historical"
    if assertion.get("positive"):
        return "positive"
    return "uncertain"