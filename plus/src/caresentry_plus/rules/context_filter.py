"""Clinical assertion, negation, and context extraction filter.

Analyzes sentence windows to determine assertion modality:
- AFFIRMED: Active, confirmed diagnosis, current order, or genuine allergy.
- NEGATED: Ruled out, denied, or absent (e.g. NKDA, denies penicillin allergy).
- HISTORICAL: Historical tolerance or discontinued medication (e.g. tolerated amoxicillin in 2019).
- FAMILY_HISTORY: Attributed to a relative rather than the patient.
- AMBIGUOUS: Uncertain or questionable mention; fails safe by triggering clinical review.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AssertionStatus(str, Enum):
    AFFIRMED = "AFFIRMED"
    NEGATED = "NEGATED"
    HISTORICAL = "HISTORICAL"
    FAMILY_HISTORY = "FAMILY_HISTORY"
    AMBIGUOUS = "AMBIGUOUS"


class AllergySeverity(str, Enum):
    ANAPHYLAXIS = "ANAPHYLAXIS"
    MILD_OR_INTOLERANCE = "MILD_OR_INTOLERANCE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class ContextAssertion:
    entity: str
    status: AssertionStatus
    severity: AllergySeverity
    evidence_snippet: str
    is_active_risk: bool
    confidence: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "status": self.status.value,
            "severity": self.severity.value,
            "evidence_snippet": self.evidence_snippet,
            "is_active_risk": self.is_active_risk,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


# Negation regex patterns
NEGATION_PATTERNS = [
    r"\b(?:no\s+known\s+(?:drug\s+)?allerg(?:y|ies))\b",
    r"\b(?:nkda|nkdra|nka)\b",
    r"\b(?:denies|denied|denying)\s+(?:any\s+)?(?:allerg(?:y|ies)|history\s+of\s+allerg(?:y|ies))\b",
    r"\b(?:no\s+(?:documented\s+)?history\s+of\s+allerg(?:y|ies))\b",
    r"\b(?:no|not|never|without|free\s+of|negative\s+for)\s+(?:known\s+)?(?:allerg(?:y|ies)\s+to\s+)?\b",
    r"\b(?:allergy|allergies|adverse\s+reaction)\s+(?:is\s+|are\s+|was\s+|were\s+)?(?:ruled\s+out|excluded|negated|unlikely)\b",
    r"\b(?:ruled\s+out\s+(?:for\s+)?allerg(?:y|ies))\b",
    r"\b(?:does\s+not\s+have\s+(?:a\s+)?(?:known\s+)?allerg(?:y|ies))\b",
]

# Historical tolerance patterns
HISTORICAL_TOLERANCE_PATTERNS = [
    r"\btolerated\s+[\w\s,-]{1,30}?(?:without\s+(?:issue|reaction|adverse|complication)|in\s+\d{4}|well|previously)\b",
    r"\bcompleted\s+[\w\s,-]{1,30}?(?:course|treatment)\s+(?:last\s+year|previously|in\s+\d{4})?\s*without\s+(?:reaction|incident|complication|issue)\b",
    r"\btook\s+[\w\s,-]{1,30}?(?:in\s+\d{4}|in\s+past|previously)?\s*(?:with\s+no\s+(?:problem|reaction|issue)|without\s+(?:complication|incident|reaction|adverse|issue))\b",
    r"\bno\s+reaction\s+(?:when|upon|after)\s+(?:taking|administered|receiving)\b",
    r"\bchildhood\s+reaction\s+[\w\s,-]{0,20}?(?:resolved|outgrown|negative\s+on\s+re-challenge)\b",
    r"\bdiscontinued\s+[\w\s,-]{1,20}?(?:\d+\s+(?:years?|months?)\s+ago|in\s+\d{4})\b",
    r"\bformerly\s+(?:prescribed|on|taking)\b",
    r"\bpreviously\s+(?:received|took|on|prescribed)\s+[\w\s,-]{1,20}?(?:without|with\s+no)\b",
]

# Family history patterns
FAMILY_HISTORY_PATTERNS = [
    r"\b(?:patient'?s\s+)?(?:mother|father|sister|brother|parent|sibling|daughter|son|family|maternal|paternal)\s+(?:has|had|with|developed|reported|history\s+of|is\s+allergic)\b",
    r"\b(?:family\s+history\s+of)\b",
    r"\b(?:fhx|fh)\s*:\s*[\w\s,-]{1,30}?\ballerg\w+\b",
    r"\b(?:maternal|paternal|family)\s+(?:history\s+notable\s+for|allergy)\b",
]

# Ambiguity patterns
AMBIGUITY_PATTERNS = [
    r"\b(?:possible|questionable|uncertain|unclear|suspected|probable|equivocal|unconfirmed)\b",
    r"\b(?:patient\s+thinks|reports\s+possible|cannot\s+recall\s+if)\b",
]

# Allergy severity patterns
ANAPHYLAXIS_PATTERNS = [
    r"\b(?:anaphylaxis|anaphylactic|angioedema|throat\s+closing|respiratory\s+arrest|intubation|hypotension|airway|epipen|epinephrine)\b",
]

MILD_SEVERITY_PATTERNS = [
    r"\b(?:mild\s+rash|rash|itching|pruritus|nausea|stomach\s+upset|diarrhea|gi\s+upset|headache|hives)\b",
]


class ContextFilter:
    """Pre-processes records and evaluates assertion context and negation status."""

    def __init__(self):
        self._compiled_negations = [re.compile(p, re.IGNORECASE) for p in NEGATION_PATTERNS]
        self._compiled_historical = [re.compile(p, re.IGNORECASE) for p in HISTORICAL_TOLERANCE_PATTERNS]
        self._compiled_family = [re.compile(p, re.IGNORECASE) for p in FAMILY_HISTORY_PATTERNS]
        self._compiled_ambiguity = [re.compile(p, re.IGNORECASE) for p in AMBIGUITY_PATTERNS]
        self._compiled_anaphylaxis = [re.compile(p, re.IGNORECASE) for p in ANAPHYLAXIS_PATTERNS]
        self._compiled_mild = [re.compile(p, re.IGNORECASE) for p in MILD_SEVERITY_PATTERNS]

    def analyze_assertion(self, sentence: str, target_entity: str) -> ContextAssertion:
        """Evaluate clinical context for a target entity within a sentence.
        
        Guarantees fail-safe behavior: ambiguous assertions are marked active risk.
        """
        s_clean = sentence.strip()
        s_lower = s_clean.lower()
        t_lower = target_entity.lower()

        # Isolate the sentence containing the target entity
        sentences = re.split(r"(?<=[.!?\n])\s+", s_clean)
        target_sent = s_clean
        for sent in sentences:
            if re.search(rf"\b{re.escape(t_lower)}\b", sent.lower()) or re.search(re.escape(t_lower), sent.lower()):
                target_sent = sent.strip()
                break

        sent_lower = target_sent.lower()
        m_ent = re.search(rf"\b{re.escape(t_lower)}\b", sent_lower) or re.search(re.escape(t_lower), sent_lower)

        # Context window around entity in target sentence
        start = max(0, m_ent.start() - 50) if m_ent else 0
        end = min(len(target_sent), m_ent.end() + 50) if m_ent else len(target_sent)
        window = target_sent[start:end]
        window_lower = window.lower()

        # 1. Family History Check
        for pat in self._compiled_family:
            if pat.search(window_lower) or pat.search(sent_lower):
                return ContextAssertion(
                    entity=target_entity,
                    status=AssertionStatus.FAMILY_HISTORY,
                    severity=AllergySeverity.UNSPECIFIED,
                    evidence_snippet=target_sent,
                    is_active_risk=False,
                    confidence=0.92,
                    rationale="Mention attributed to family member; patient active risk is not affirmed.",
                )

        # 2. Historical Tolerance Check (e.g. tolerated drug without issue)
        for pat in self._compiled_historical:
            if pat.search(window_lower) or pat.search(sent_lower):
                return ContextAssertion(
                    entity=target_entity,
                    status=AssertionStatus.HISTORICAL,
                    severity=AllergySeverity.UNSPECIFIED,
                    evidence_snippet=target_sent,
                    is_active_risk=False,
                    confidence=0.90,
                    rationale="Documented historical tolerance or past resolved exposure; not an active barrier.",
                )

        # 3. Explicit Negation Check (e.g. no known allergy, denied, NKDA)
        for pat in self._compiled_negations:
            if m_ent:
                prefix = sent_lower[max(0, m_ent.start() - 40) : m_ent.start()]
                postfix = sent_lower[m_ent.end() : min(len(sent_lower), m_ent.end() + 40)]
                if pat.search(prefix) or pat.search(postfix) or pat.search(sent_lower):
                    return ContextAssertion(
                        entity=target_entity,
                        status=AssertionStatus.NEGATED,
                        severity=AllergySeverity.UNSPECIFIED,
                        evidence_snippet=target_sent,
                        is_active_risk=False,
                        confidence=0.95,
                        rationale="Explicitly negated or ruled out.",
                    )
            elif pat.search(sent_lower):
                return ContextAssertion(
                    entity=target_entity,
                    status=AssertionStatus.NEGATED,
                    severity=AllergySeverity.UNSPECIFIED,
                    evidence_snippet=target_sent,
                    is_active_risk=False,
                    confidence=0.95,
                    rationale="Explicitly negated clinical assertion.",
                )

        # 4. Ambiguity Check -> Fail Safe (Treat as active risk)
        for pat in self._compiled_ambiguity:
            if pat.search(window_lower) or pat.search(sent_lower):
                return ContextAssertion(
                    entity=target_entity,
                    status=AssertionStatus.AMBIGUOUS,
                    severity=AllergySeverity.UNSPECIFIED,
                    evidence_snippet=target_sent,
                    is_active_risk=True,  # FAIL SAFE
                    confidence=0.75,
                    rationale="Ambiguous or questionable assertion; preserved as active risk for patient safety.",
                )

        # 5. Determine Allergy Severity if affirmed
        severity = AllergySeverity.UNSPECIFIED
        for pat in self._compiled_anaphylaxis:
            if pat.search(sent_lower):
                severity = AllergySeverity.ANAPHYLAXIS
                break
        if severity == AllergySeverity.UNSPECIFIED:
            for pat in self._compiled_mild:
                if pat.search(sent_lower):
                    severity = AllergySeverity.MILD_OR_INTOLERANCE
                    break

        return ContextAssertion(
            entity=target_entity,
            status=AssertionStatus.AFFIRMED,
            severity=severity,
            evidence_snippet=target_sent,
            is_active_risk=True,
            confidence=0.98,
            rationale="Affirmed clinical finding or active patient constraint.",
        )

    def filter_active_constraints(
        self,
        text: str,
        candidates: List[Tuple[str, str]],
    ) -> Tuple[List[ContextAssertion], List[ContextAssertion]]:
        """Process candidate mentions (sentence, entity) and divide into active vs suppressed."""
        active: List[ContextAssertion] = []
        suppressed: List[ContextAssertion] = []

        for sentence, entity in candidates:
            assertion = self.analyze_assertion(sentence, entity)
            if assertion.is_active_risk:
                active.append(assertion)
            else:
                suppressed.append(assertion)

        return active, suppressed
