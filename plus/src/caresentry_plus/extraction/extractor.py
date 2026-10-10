"""Structured Clinical Extraction Engine.

Extracts allergies, active medications, laboratory parameters, and critical
diagnoses from raw EHR notes into strongly-typed schemas without LLM dependencies.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from caresentry_plus.ontology.normalizer import DrugNormalizer
from caresentry_plus.rules.context_filter import ContextFilter


@dataclass
class ExtractedAllergy:
    allergen: str
    canonical_class: str
    severity: str
    evidence: str


@dataclass
class ExtractedMedication:
    drug_name: str
    canonical_name: str
    drug_class: str
    is_anticoagulant: bool
    evidence: str


@dataclass
class ExtractedLab:
    name: str
    value: float
    unit: str
    is_critical: bool
    evidence: str


@dataclass
class ExtractedDiagnosis:
    diagnosis: str
    category: str
    evidence: str


@dataclass
class ClinicalExtractionResult:
    allergies: List[ExtractedAllergy] = field(default_factory=list)
    medications: List[ExtractedMedication] = field(default_factory=list)
    labs: List[ExtractedLab] = field(default_factory=list)
    diagnoses: List[ExtractedDiagnosis] = field(default_factory=list)
    patient_age: Optional[int] = None
    patient_sex: Optional[str] = None
    patient_weight_kg: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allergies": [asdict(a) for a in self.allergies],
            "medications": [asdict(m) for m in self.medications],
            "labs": [asdict(l) for l in self.labs],
            "diagnoses": [asdict(d) for d in self.diagnoses],
            "patient_age": self.patient_age,
            "patient_sex": self.patient_sex,
            "patient_weight_kg": self.patient_weight_kg,
        }


class StructuredExtractor:
    """Offline, deterministic clinical entity extractor."""

    def __init__(
        self,
        normalizer: Optional[DrugNormalizer] = None,
        context_filter: Optional[ContextFilter] = None,
        llm_assisted: bool = False,
    ):
        self.normalizer = normalizer or DrugNormalizer()
        self.context_filter = context_filter or ContextFilter()
        self.llm_assisted = llm_assisted  # Off by default per NFR-B1

    def extract(self, raw_ehr: str) -> ClinicalExtractionResult:
        """Parse raw clinical text into structured clinical extraction result."""
        result = ClinicalExtractionResult()

        # Demographics
        age_m = re.search(r"\b(\d{1,3})\s*[- ]?\s*(?:year[s]?[- ]?old|yo|y\.o\.)\b", raw_ehr, re.IGNORECASE)
        if age_m:
            result.patient_age = int(age_m.group(1))

        if re.search(r"\b(?:female|woman|lady)\b", raw_ehr, re.IGNORECASE):
            result.patient_sex = "female"
        elif re.search(r"\b(?:male|man|gentleman)\b", raw_ehr, re.IGNORECASE):
            result.patient_sex = "male"

        wt_m = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*(?:kg|kilos)\b", raw_ehr, re.IGNORECASE)
        if wt_m:
            result.patient_weight_kg = float(wt_m.group(1))

        # Labs
        egfr_m = re.search(r"(?:\(?egfr\)?|gfr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,3}(?:\.[0-9]+)?)", raw_ehr, re.IGNORECASE)
        if egfr_m:
            val = float(egfr_m.group(1))
            result.labs.append(
                ExtractedLab(
                    name="eGFR",
                    value=val,
                    unit="mL/min/1.73m2",
                    is_critical=val < 30.0,
                    evidence=egfr_m.group(0),
                )
            )

        creat_m = re.search(r"(?:creatinine|creat|scr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,2}(?:\.[0-9]+)?)", raw_ehr, re.IGNORECASE)
        if creat_m:
            val = float(creat_m.group(1))
            result.labs.append(
                ExtractedLab(
                    name="Creatinine",
                    value=val,
                    unit="mg/dL",
                    is_critical=val >= 2.0,
                    evidence=creat_m.group(0),
                )
            )

        potassium_m = re.search(r"(?:potassium|k\+?)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,2}(?:\.[0-9]+)?)", raw_ehr, re.IGNORECASE)
        if potassium_m:
            val = float(potassium_m.group(1))
            result.labs.append(
                ExtractedLab(
                    name="Potassium",
                    value=val,
                    unit="mEq/L",
                    is_critical=val >= 5.5,
                    evidence=potassium_m.group(0),
                )
            )

        # High-risk Diagnoses
        diagnosis_patterns = [
            ("Renal Failure / CKD", "renal", r"\b(?:chronic\s+kidney\s+disease|ckd(?:\s*stage\s*[1-5])?|renal\s+failure|end[- ]stage\s+renal|esrd|acute\s+kidney\s+injury|aki)\b"),
            ("Atrial Fibrillation", "cardiovascular", r"\b(?:atrial\s+fibrillation|a-fib|afib|flutter)\b"),
            ("Heart Failure", "cardiovascular", r"\b(?:congestive\s+heart\s+failure|chf|hfref|hfpef|heart\s+failure)\b"),
            ("Gastrointestinal Bleed", "bleeding_risk", r"\b(?:gi\s+bleed|gastrointestinal\s+hemorrhage|peptic\s+ulcer|melena|hematemesis)\b"),
            ("Diabetes Mellitus", "metabolic", r"\b(?:diabetes\s+mellitus|type\s*[12]\s+diabetes|t2dm|t1dm)\b"),
        ]

        for diag_label, cat, pat in diagnosis_patterns:
            m = re.search(pat, raw_ehr, re.IGNORECASE)
            if m:
                snippet = raw_ehr[max(0, m.start() - 20) : min(len(raw_ehr), m.end() + 20)].strip()
                result.diagnoses.append(
                    ExtractedDiagnosis(
                        diagnosis=diag_label,
                        category=cat,
                        evidence=snippet,
                    )
                )

        # Allergies & Medications via Normalizer & ContextFilter
        sentences = re.split(r"[.\n;]+", raw_ehr)
        seen_allergens = set()
        seen_meds = set()

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            entities = self.normalizer.extract_and_normalize(s_clean)
            for ent in entities:
                assertion = self.context_filter.analyze_assertion(s_clean, ent.raw_term)

                # Check if this sentence is an allergy section
                is_allergy_context = bool(
                    re.search(r"\b(?:allerg\w*|hypersensitivity|reaction|anaphylaxis|aerd|adverse)\b", s_clean, re.IGNORECASE)
                )

                if is_allergy_context and assertion.is_active_risk:
                    if ent.canonical_name not in seen_allergens:
                        seen_allergens.add(ent.canonical_name)
                        result.allergies.append(
                            ExtractedAllergy(
                                allergen=ent.raw_term,
                                canonical_class=ent.drug_class,
                                severity=assertion.severity.value,
                                evidence=s_clean,
                            )
                        )
                elif assertion.is_active_risk and not is_allergy_context:
                    # Active medication
                    if ent.canonical_name not in seen_meds:
                        seen_meds.add(ent.canonical_name)
                        result.medications.append(
                            ExtractedMedication(
                                drug_name=ent.raw_term,
                                canonical_name=ent.canonical_name,
                                drug_class=ent.drug_class,
                                is_anticoagulant=(ent.drug_class == "anticoagulant"),
                                evidence=s_clean,
                            )
                        )

        return result
