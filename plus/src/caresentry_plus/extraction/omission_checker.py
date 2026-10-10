"""Reverse Omission Sentry.

Validates that critical clinical constraints and alerts documented in the EHR
are acknowledged and retained in the patient discharge summary.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from caresentry_plus.extraction.extractor import (
    ClinicalExtractionResult,
    StructuredExtractor,
)
from caresentry_plus.ontology.normalizer import DrugNormalizer


@dataclass
class ClinicalOmission:
    category: str
    constraint: str
    record_evidence: str
    severity: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OmissionChecker:
    """Reverse verification gate testing summary completeness against extracted ground truth constraints."""

    def __init__(
        self,
        extractor: Optional[StructuredExtractor] = None,
        normalizer: Optional[DrugNormalizer] = None,
    ):
        self.normalizer = normalizer or DrugNormalizer()
        self.extractor = extractor or StructuredExtractor(normalizer=self.normalizer)

    def check_omissions(
        self,
        raw_ehr: str,
        summary_content: str,
        extracted_data: Optional[ClinicalExtractionResult] = None,
    ) -> List[ClinicalOmission]:
        """Perform reverse check returning all omitted critical safety invariants."""
        if extracted_data is None:
            extracted_data = self.extractor.extract(raw_ehr)

        omissions: List[ClinicalOmission] = []
        summary_lower = summary_content.lower()

        # 1. Reverse Allergy Check
        # Every documented allergy in raw EHR must be acknowledged or avoided in discharge summary
        for allergy in extracted_data.allergies:
            allergen_norm = self.normalizer.normalize(allergy.allergen)
            canon = allergen_norm.canonical_name if allergen_norm else allergy.allergen.lower()
            drug_class = allergen_norm.drug_class if allergen_norm else allergy.canonical_class.lower()

            # Check if mentioned in summary
            allergen_mentioned = bool(
                re.search(rf"\b{re.escape(allergy.allergen.lower())}\b", summary_lower)
                or re.search(rf"\b{re.escape(canon)}\b", summary_lower)
                or re.search(rf"\b{re.escape(drug_class)}\b", summary_lower)
            )

            # If not mentioned at all in summary, check if summary has an allergy section
            has_allergy_section = bool(
                re.search(r"\b(?:allerg|nkda|adverse\s+reaction)\b", summary_lower)
            )

            if not allergen_mentioned:
                omissions.append(
                    ClinicalOmission(
                        category="ALLERGY_CONSTRAINT",
                        constraint=f"Documented {allergy.allergen.upper()} Allergy ({allergy.canonical_class.upper()}) omitted from discharge summary.",
                        record_evidence=allergy.evidence,
                        severity="CRITICAL" if allergy.severity == "ANAPHYLAXIS" else "HIGH",
                        remediation=f"Explicitly document patient's {allergy.allergen} allergy and cross-reactivity warnings in discharge instructions.",
                    )
                )

        # 2. Reverse Renal Precaution Check
        critical_renal = [lab for lab in extracted_data.labs if lab.name == "eGFR" and lab.is_critical]
        renal_diag = [d for d in extracted_data.diagnoses if d.category == "renal"]

        if critical_renal or renal_diag:
            renal_acknowledged = bool(
                re.search(
                    r"\b(?:renal|kidney|egfr|gfr|creatinine|ckd|nephro|dialysis)\b",
                    summary_lower,
                )
            )
            if not renal_acknowledged:
                evidence = critical_renal[0].evidence if critical_renal else renal_diag[0].evidence
                omissions.append(
                    ClinicalOmission(
                        category="RENAL_PRECAUTION",
                        constraint="Severe Renal Impairment (eGFR < 30 mL/min / CKD) completely omitted from summary.",
                        record_evidence=evidence,
                        severity="CRITICAL",
                        remediation="Include renal dosing precautions and nephrology follow-up directives in discharge plan.",
                    )
                )

        # 3. Anticoagulation Continuity Check
        anticoagulants = [m for m in extracted_data.medications if m.is_anticoagulant]
        for ac in anticoagulants:
            # Check if anticoagulant or anticoagulation management is mentioned in summary
            ac_mentioned = bool(
                re.search(rf"\b{re.escape(ac.drug_name.lower())}\b", summary_lower)
                or re.search(rf"\b{re.escape(ac.canonical_name.lower())}\b", summary_lower)
                or re.search(r"\b(?:anticoagulat|blood\s+thinner|inr|bleeding\s+precaution)\b", summary_lower)
            )
            if not ac_mentioned:
                omissions.append(
                    ClinicalOmission(
                        category="ANTICOAGULATION_CONTINUITY",
                        constraint=f"High-risk Anticoagulant ({ac.drug_name.upper()}) continuation/discontinuation plan omitted.",
                        record_evidence=ac.evidence,
                        severity="HIGH",
                        remediation=f"Specify explicit instructions regarding {ac.drug_name} dosage, timing, and hemorrhage precautions.",
                    )
                )

        # 4. Critical Hyperkalemia Check
        hyperkalemia_labs = [l for l in extracted_data.labs if l.name == "Potassium" and l.is_critical]
        if hyperkalemia_labs:
            k_acknowledged = bool(
                re.search(r"\b(?:potassium|hyperkalemia|k\+)\b", summary_lower)
            )
            if not k_acknowledged:
                omissions.append(
                    ClinicalOmission(
                        category="CRITICAL_LAB_ALERT",
                        constraint="Life-threatening Hyperkalemia (Potassium >= 5.5 mEq/L) omitted from discharge summary.",
                        record_evidence=hyperkalemia_labs[0].evidence,
                        severity="CRITICAL",
                        remediation="Document elevated potassium level and repeat electrolyte panel instructions at discharge.",
                    )
                )

        return omissions
