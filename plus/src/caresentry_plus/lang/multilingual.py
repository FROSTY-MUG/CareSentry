"""Multilingual Clinical Aliases & Patient Readability Scorer (F-16).

Provides multilingual mapping (Hindi & Spanish) for core allergy and pharmacological concepts,
and calculates readability metrics (Flesch-Kincaid Grade Level, Flesch Reading Ease)
to evaluate patient-facing discharge summary accessibility.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

# Documented Multilingual Vocabulary Coverage
MULTILINGUAL_CLINICAL_MAP: Dict[str, Dict[str, List[str]]] = {
    "penicillin": {
        "hi": ["पेनिसिलिन", "पेनिसिलिन एलर्जी", "एमोक्सिसिलिन"],
        "es": ["penicilina", "alergia a la penicilina", "amoxicilina"],
    },
    "sulfonamide": {
        "hi": ["सल्फा", "सल्फा दवा", "बैक्त्रिम"],
        "es": ["sulfa", "sulfonamida", "alergia a las sulfas", "bactrim"],
    },
    "nsaid": {
        "hi": ["इबुप्रोफेन", "दर्दनिवारक दवा", "एस्पिरिन"],
        "es": ["ibuprofeno", "antiinflamatorio", "aspirina", "naproxeno"],
    },
    "renal_impairment": {
        "hi": ["गुर्दे की विफलता", "किडनी रोग", "गुर्दे की खराबी"],
        "es": ["insuficiencia renal", "enfermedad renal crónica", "daño renal"],
    },
    "anticoagulant": {
        "hi": ["खून पतला करने वाली दवा", "वारफारिन"],
        "es": ["anticoagulante", "diluyente de la sangre", "warfarina"],
    },
}

LANGUAGE_COVERAGE_NOTES = {
    "supported_languages": ["en", "hi", "es"],
    "verified_concepts": ["penicillin", "sulfonamide", "nsaid", "renal_impairment", "anticoagulant"],
    "known_gaps": [
        "Regional dialectal phonetics and non-standard transliterations in Hindi (Devanagari script) require standardized spelling.",
        "Compound brand names in regional markets (e.g. Augmentin Indian generic brands like Moxikind-CV) require manual inclusion.",
        "Clinical verification note: No machine translations are treated as clinical invariants without explicit lexicon entry.",
    ],
}


@dataclass
class ReadabilityMetrics:
    flesch_reading_ease: float
    flesch_kincaid_grade_level: float
    total_words: int
    total_sentences: int
    average_words_per_sentence: float
    reading_accessibility: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultilingualLanguageSentry:
    """Multilingual term mapper and patient summary readability evaluator."""

    def __init__(self):
        self.multilingual_map = MULTILINGUAL_CLINICAL_MAP
        self.coverage_notes = LANGUAGE_COVERAGE_NOTES

    def detect_multilingual_mentions(self, text: str) -> List[Dict[str, str]]:
        """Identify Hindi and Spanish clinical constraint mentions in text."""
        mentions = []
        text_lower = text.lower()

        for canonical_concept, lang_dict in self.multilingual_map.items():
            for lang, terms in lang_dict.items():
                for term in terms:
                    if term.lower() in text_lower:
                        mentions.append({
                            "term": term,
                            "canonical_concept": canonical_concept,
                            "language": lang,
                        })
        return mentions

    @staticmethod
    def count_syllables(word: str) -> int:
        """Estimate syllable count in an English word."""
        w = word.lower().strip()
        if not w:
            return 0
        w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
        w = re.sub(r"^y", "", w)
        syllables = len(re.findall(r"[aeiouy]{1,2}", w))
        return max(1, syllables)

    def calculate_readability(self, text: str) -> ReadabilityMetrics:
        """Calculate Flesch-Kincaid Grade Level and Reading Ease for patient summaries."""
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        words = re.findall(r"\b[A-Za-z]+\b", text)

        num_sentences = max(1, len(sentences))
        num_words = max(1, len(words))

        total_syllables = sum(self.count_syllables(w) for w in words)

        asl = num_words / num_sentences  # Average Sentence Length
        asw = total_syllables / num_words  # Average Syllables per Word

        # Flesch Reading Ease: 206.835 - 1.015 * ASL - 84.6 * ASW
        reading_ease = 206.835 - (1.015 * asl) - (84.6 * asw)
        reading_ease = max(0.0, min(100.0, reading_ease))

        # Flesch-Kincaid Grade Level: 0.39 * ASL + 11.8 * ASW - 15.59
        grade_level = (0.39 * asl) + (11.8 * asw) - 15.59
        grade_level = max(0.0, round(grade_level, 1))

        if grade_level <= 8.0:
            accessibility = "PATIENT_ACCESSIBLE (Recommended Grade 6-8)"
        elif grade_level <= 12.0:
            accessibility = "MODERATE_COMPLEXITY (High School Reading Level)"
        else:
            accessibility = "COMPLEX_CLINICAL_JARGON (College / Professional)"

        return ReadabilityMetrics(
            flesch_reading_ease=round(reading_ease, 1),
            flesch_kincaid_grade_level=grade_level,
            total_words=num_words,
            total_sentences=num_sentences,
            average_words_per_sentence=round(asl, 1),
            reading_accessibility=accessibility,
        )
