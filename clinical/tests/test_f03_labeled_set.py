"""Labeled sentence set for F-03 Negation and Context Filter precision/recall.

Each entry is (sentence, expected_assertion, description).
expected_assertion: "positive", "negated", "historical", "uncertain", "family_history"
"""

from __future__ import annotations

from typing import List, Tuple

LABELED_SET: List[Tuple[str, str]] = [
    # === POSITIVE ALERIES (current, asserted) ===
    ("Patient has a penicillin allergy.", "positive",
     "Simple positive allergy statement"),
    ("Patient is allergic to penicillin.", "positive",
     "Standard allergy formulation"),
    ("Patient has documented penicillin allergy.", "positive",
     "With documentation qualifier"),
    ("Patient reports penicillin allergy with hives.", "positive",
     "Allergy with symptom description"),
    ("Patient has documented severe penicillin allergy.", "positive",
     "Severe allergy annotation"),
    ("Patient is allergic to penicillin and amoxicillin.", "positive",
     "Multiple antibiotic allergy"),
    ("Patient has a known penicillin hypersensitivity.", "positive",
     "Hypersensitivity term"),
    ("Patient experienced anaphylaxis with penicillin.", "positive",
     "Anaphylaxis event"),
    ("Patient has penicillin allergy documented in chart.", "positive",
     "Chart documentation"),
    ("Patient reports penicillin allergy and swelling.", "positive",
     "Allergy with angioedema"),
    # === NEGATED ALERIES ===
    ("Patient has no known drug allergies.", "negated",
     "Explicit no-allergy statement"),
    ("No known drug allergies.", "negated",
     "Bare no-allergy statement"),
    ("Patient denies any drug allergies.", "negated",
     "Denial of allergies"),
    ("No penicillin allergy.", "negated",
     "Direct negation"),
    ("Patient is not allergic to penicillin.", "negated",
     "Explicit negation"),
    ("No history of drug allergy.", "negated",
     "No history phrasing"),
    ("No known hypersensitivity to medications.", "negated",
     "Broad negation"),
    ("Patient has no history of drug reactions.", "negated",
     "No reaction history"),
    ("No allergic reactions to penicillin reported.", "negated",
     "No reactions reported"),
    ("Patient reports no drug allergies.", "negated",
     "Direct patient report"),
    # === HISTORICAL ALERIES ===
    ("Patient had penicillin allergy in 2019, resolved.", "historical",
     "Historical with resolution year"),
    ("Penicillin allergy from 2018, now tolerated.", "historical",
     "Old allergy with tolerance"),
    ("Allergy to sulfa in childhood, no current allergy.", "historical",
     "Childhood allergy, no current"),
    ("Had aspirin allergy as a child, outgrew it.", "historical",
     "Outgrown childhood allergy"),
    ("Penicillin allergy noted in 2015, tests negative now.", "historical",
     "Historical with current negative"),
    # === FAMILY HISTORY ===
    ("Father has penicillin allergy.", "family_history",
     "Family history mention"),
    ("Mother has severe penicillin allergy.", "family_history",
     "Family history with severity"),
    ("Family history of drug allergies.", "family_history",
     "General family history"),
    ("Sister has penicillin allergy.", "family_history",
     "Sibling allergy"),
    # === TOLERATED / RESOLVED ===
    ("Patient tolerated penicillin in 2019.", "positive",
     "Tolerated in a specific year — this is ambiguous; default to positive but flag"),
    ("Patient tolerated amoxicillin after desensitization.", "positive",
     "Desensitization context"),
    # === NO MODIFIER / AMBIGUOUS ===
    ("Patient has penicillin.", "uncertain",
     "Bare drug mention without allergy context"),
    ("Patient received penicillin.", "uncertain",
     "Drug administration, not allergy"),
    # === SEVERITY MODIFIERS ===
    ("Patient has mild penicillin allergy.", "positive",
     "Mild severity, still positive"),
    ("Patient has severe penicillin allergy.", "positive",
     "Severe severity, still positive"),
    ("Patient has moderate penicillin allergy.", "positive",
     "Moderate severity, still positive"),
    # === RULED OUT / CLEARED ===
    ("Penicillin allergy was ruled out.", "negated",
     "Explicitly ruled out"),
    ("Allergy cleared, patient can now take penicillin.", "negated",
     "Cleared with permission"),
    # === CURRENT VS HISTORICAL CONFLICT ===
    ("Patient had penicillin allergy as a child but outgrew it.", "uncertain",
     "Conflicting: historical + possible current — fail safe uncertain"),
    ("Previously allergic to penicillin, now negative tests.", "uncertain",
     "Conflicting: past + current negative — fail safe uncertain"),
]

def get_labeled_set() -> List[Tuple[str, str]]:
    """Return the labeled sentence set for F-03 evaluation."""
    return LABELED_SET


def expected_assertion(sentence: str) -> str:
    """Return the expected assertion status for a labeled sentence."""
    for s, status, _ in LABELED_SET:
        if s == sentence:
            return status
    raise ValueError(f"Sentence not in labeled set: {sentence!r}")