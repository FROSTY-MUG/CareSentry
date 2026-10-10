"""Evidence Attribution & Hallucination Grounding Engine.

Attributes each sentence of a generated discharge summary to source EHR spans,
identifying ungrounded assertions, phantom lab numbers, and fabricated medication orders.
Enforces stricter threshold for safety-critical clinical claims.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

SAFETY_CRITICAL_KEYWORDS = [
    "prescribe", "order", "take", "daily", "mg", "po", "bid", "tid", "qid",
    "allergy", "allergic", "creatinine", "egfr", "inr", "dose", "stop", "hold",
    "discontinue", "tablets", "units", "iv", "subcutaneous"
]


@dataclass
class SentenceAttribution:
    sentence_index: int
    sentence_text: str
    is_safety_critical: bool
    supporting_ehr_spans: List[str]
    best_similarity_score: float
    status: str  # "supported" | "weak" | "unsupported"
    flagged_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GroundingReport:
    total_sentences: int
    supported_count: int
    weak_count: int
    unsupported_count: int
    safety_critical_violations: int
    overall_grounding_score: float
    sentence_attributions: List[SentenceAttribution]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceGroundingEngine:
    """Offline evidence grounding and hallucination auditor."""

    def __init__(
        self,
        supported_threshold: float = 0.40,
        weak_threshold: float = 0.25,
        safety_critical_threshold: float = 0.45,
    ):
        self.supported_threshold = supported_threshold
        self.weak_threshold = weak_threshold
        self.safety_critical_threshold = safety_critical_threshold

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences cleanly."""
        raw = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [s.strip() for s in raw if s.strip() and len(s.strip()) > 3]

    def is_safety_critical(self, sentence: str) -> bool:
        """Check if sentence contains medication orders, dosages, or lab claims."""
        s_lower = sentence.lower()
        return any(re.search(rf"\b{k}\b", s_lower) for k in SAFETY_CRITICAL_KEYWORDS)

    def extract_source_paragraphs(self, source_ehr: str) -> List[str]:
        """Split source EHR into candidate paragraphs / sections."""
        paras = [p.strip() for p in source_ehr.split("\n") if p.strip()]
        return paras

    def find_best_supporting_spans(
        self, sentence: str, source_paras: List[str]
    ) -> Tuple[float, List[str]]:
        """Calculate maximum lexical and token overlap score against source EHR paragraphs."""
        best_score = 0.0
        best_spans = []

        s_words = set(re.findall(r"\w+", sentence.lower()))
        # Filter common stopwords for precise clinical matching
        stopwords = {"the", "a", "an", "is", "was", "with", "for", "in", "on", "at", "to", "of", "and", "or"}
        content_words = {w for w in s_words if w not in stopwords and len(w) > 2}
        if not content_words:
            content_words = s_words

        if not content_words:
            return 0.0, []

        # Overall EHR check for core medication / entity containment
        full_ehr = " ".join(source_paras).lower()
        core_entities_found = [w for w in content_words if w in full_ehr]
        ehr_containment = len(core_entities_found) / max(len(content_words), 1)

        # Medication cross-check
        from caresentry_guard.lexicon.provider import get_lexicon_provider
        lexicon = get_lexicon_provider()
        known_drugs = getattr(lexicon, "get_all_known_drugs", lambda: set())()
        drugs_in_sentence = [w for w in s_words if w in known_drugs]
        
        has_unsupported_drug = False
        has_supported_drug = False
        if drugs_in_sentence:
            for d in drugs_in_sentence:
                if d in full_ehr:
                    has_supported_drug = True
                else:
                    has_unsupported_drug = True

        for p in source_paras:
            p_lower = p.lower()
            p_words = set(re.findall(r"\w+", p_lower))
            if not p_words:
                continue

            intersection = content_words.intersection(p_words)
            containment = len(intersection) / len(content_words)

            seq_ratio = difflib.SequenceMatcher(None, sentence.lower(), p_lower).ratio()
            score = 0.5 * containment + 0.35 * ehr_containment + 0.15 * min(seq_ratio * 2.0, 1.0)

            if has_supported_drug:
                score = min(score + 0.25, 1.0)
            if has_unsupported_drug:
                score = min(score, 0.20)

            if score > best_score:
                best_score = score
                best_spans = [p[:160] + "..." if len(p) > 160 else p]

        return round(best_score, 4), best_spans

    def audit_grounding(self, source_ehr: str, summary_text: str) -> GroundingReport:
        """Execute evidence grounding audit across all summary sentences."""
        sentences = self.split_sentences(summary_text)
        source_paras = self.extract_source_paragraphs(source_ehr)

        attributions: List[SentenceAttribution] = []
        supported_cnt = 0
        weak_cnt = 0
        unsupported_cnt = 0
        safety_critical_violations = 0
        scores_sum = 0.0

        for idx, s in enumerate(sentences):
            crit = self.is_safety_critical(s)
            score, spans = self.find_best_supporting_spans(s, source_paras)
            scores_sum += score

            flagged = []
            req_thresh = (
                self.safety_critical_threshold if crit else self.supported_threshold
            )

            if score >= req_thresh:
                status = "supported"
                supported_cnt += 1
            elif score >= self.weak_threshold:
                status = "weak"
                weak_cnt += 1
                flagged.append(f"Borderline evidence match (score {score:.2f} < {req_thresh:.2f})")
                if crit:
                    safety_critical_violations += 1
                    flagged.append("Safety-critical clinical sentence has insufficient EHR evidence")
            else:
                status = "unsupported"
                unsupported_cnt += 1
                flagged.append(f"Ungrounded claim: No supporting evidence in EHR (score {score:.2f})")
                if crit:
                    safety_critical_violations += 1
                    flagged.append("Fabricated or unsupported medication / lab claim")

            attributions.append(
                SentenceAttribution(
                    sentence_index=idx,
                    sentence_text=s,
                    is_safety_critical=crit,
                    supporting_ehr_spans=spans,
                    best_similarity_score=score,
                    status=status,
                    flagged_reasons=flagged,
                )
            )

        total_s = max(len(sentences), 1)
        overall_score = round(scores_sum / total_s, 4)

        return GroundingReport(
            total_sentences=len(sentences),
            supported_count=supported_cnt,
            weak_count=weak_cnt,
            unsupported_count=unsupported_cnt,
            safety_critical_violations=safety_critical_violations,
            overall_grounding_score=overall_score,
            sentence_attributions=attributions,
        )
