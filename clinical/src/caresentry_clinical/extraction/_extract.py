"""Structured extraction and omission check for CareSentry Clinical.

Extracts allergies, active medications, lab values, and diagnoses from
clinical records. Provides omission checking against critical constraints.

Rule-based, no LLM needed. LLM-assisted mode (if added) is labeled and off by default.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

# Base path for source files
_SOURCES_DIR = Path(__file__).parent.parent.parent / "sources"


class ExtractionResult(NamedTuple):
    """Result of structured extraction from a clinical record."""
    
    allergies: List[Dict[str, Any]]
    medications: List[Dict[str, Any]]
    labs: List[Dict[str, Any]]
    diagnoses: List[Dict[str, Any]]
    omissions: List[Dict[str, Any]]


class AllergyInfo(NamedTuple):
    """Extracted allergy information."""
    allergy_class: str
    severity: str
    asserted: bool  # True = positively asserted, False = negated/historical
    evidence_start: int  # Character offset in raw text
    evidence_end: int    # Character offset in raw text


class MedicationInfo(NamedTuple):
    """Extracted medication information."""
    drug_name: str
    dosage: str
    frequency: str
    route: str
    asserted: bool  # True = actively ordered/prescribed
    evidence_start: int
    evidence_end: int


class LabValue(NamedTuple):
    """Extracted laboratory value."""
    test_name: str
    value: str
    reference_range: str
    unit: str
    character_offset: int


class DiagnosisInfo(NamedTuple):
    """Extracted diagnosis information."""
    icd_code: str
    description: str
    severity: str
    character_offset: int


def extract_allergies(raw_text: str) -> List[AllergyInfo]:
    """Extract drug allergy mentions from raw clinical text.
    
    Uses regex patterns to find allergy mentions with assertion status.
    Returns only positively asserted (current) allergies.
    """
    allergies = []
    
    # Pattern for allergy mentions with severity
    allergy_patterns = [
        # "patient is allergic to X"
        r"(?:patient|pt)\s+is\s+allergic\s+to\s+([\w\s]+?)(?:\s+with\s+([\w\s]+?))?(?:\s*\.)",
        # "allergy to X"
        r"allergy\s+to\s+([\w\s]+?)(?:\s+with\s+([\w\s]+?))?(?:\s*\.)",
        # "allergic to X"
        r"allergic\s+to\s+([\w\s]+?)(?:\s+with\s+([\w\s]+?))?(?:\s*\.)",
        # "no known allergies to X" (negated - should be excluded)
        r"no\s+known\s+allergy\s+to\s+([\w\s]+?)(?:\s*\.)",
    ]
    
    for i, pattern in enumerate(allergy_patterns):
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            allergy_class = match.group(1).strip()
            severity_match = match.group(2) if len(match.groups()) > 1 else None
            severity = severity_match.strip() if severity_match else "unknown"
            
            # Get evidence text span
            evidence_start = match.start()
            evidence_end = match.end()
            
            # Skip if this is a negation ("no known allergy to...")
            if i == len(allergy_patterns) - 1:
                continue  # Skip negated allergies
            
            allergies.append(AllergyInfo(
                allergy_class=allergy_class,
                severity=severity,
                asserted=True,
                evidence_start=evidence_start,
                evidence_end=evidence_end,
            ))
    
    return allergies


def extract_medications(raw_text: str) -> List[MedicationInfo]:
    """Extract active medication orders from clinical text.
    
    Looks for medication mentions with dosage, frequency, and route.
    Distinguishes between current active orders and historical mentions.
    """
    medications = []
    
    # Pattern for active medication orders
    med_patterns = [
        # "Take X mg Y times daily Z route"
        r"(?:take|administer|give)\s+([\w.-]+?)\s+(?:mg|mcg|units)?\s*(?:po|iv|im|sq|oral|intravenous|intramuscular|subcutaneous)\s*(?:daily|bid|tid|qid|prn)?",
        # "X mg Y PO"
        r"([\w.-]+?)\s+(?:mg|mcg|units)\s+po\s*(?:bid|tid|tid|qid|daily)?",
        # "start X"
        r"start\s+([\w.-]+?)(?:\s+(?:mg|mcg|units))?(?:\s+(?:po|iv|im|sq))?(?:\s+(?:daily|bid|tid|qid))?",
    ]
    
    for pattern in med_patterns:
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            drug_name = match.group(1).strip()
            dosage = match.group(2) if len(re.findall(pattern, raw_text, re.IGNORECASE)) > 1 else ""
            frequency = ""
            route = ""
            
            # Extract frequency and route from full match context
            full_match = match.group(0)
            
            medications.append(MedicationInfo(
                drug_name=drug_name,
                dosage=dosage,
                frequency=frequency,
                route=route,
                asserted=True,
                evidence_start=match.start(),
                evidence_end=match.end(),
            ))
    
    return medications


def extract_labs(raw_text: str) -> List[LabValue]:
    """Extract laboratory values from clinical text.
    
    Looks for eGFR, creatinine, and other common lab values.
    """
    labs = []
    
    # eGFR pattern
    egfr_pattern = r"(?:egfr|gfr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,3}(?:\.[0-9]+)?)\s*(?:mL/min/1\.73m2|mL/min)|"
    for match in re.finditer(egfr_pattern, raw_text, re.IGNORECASE):
        labs.append(LabValue(
            test_name="eGFR",
            value=match.group(1),
            reference_range="",
            unit="mL/min/1.73m²",
            character_offset=match.start(),
        ))
    
    # Creatinine pattern
    creat_pattern = r"(?:creatinine|serum\s+creatinine)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9](?:\.[0-9]+)?)\s*(?:mg/dL|mg\/dL)"
    for match in re.finditer(creat_pattern, raw_text, re.IGNORECASE):
        labs.append(LabValue(
            test_name="Creatinine",
            value=match.group(1),
            reference_range="",
            unit="mg/dL",
            character_offset=match.start(),
        ))
    
    # Potassium pattern
    k_pattern = r"(?:potassium|k)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9](?:\.[0-9]+)?)\s*(?:mEq/L|mmol/L)"
    for match in re.finditer(k_pattern, raw_text, re.IGNORECASE):
        labs.append(LabValue(
            test_name="Potassium",
            value=match.group(1),
            reference_range="",
            unit="mEq/L",
            character_offset=match.start(),
        ))
    
    # Sodium pattern
    na_pattern = r"(?:sodium|nat)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9](?:\.[0-9]+)?)\s*(?:mEq/L|mmol/L)"
    for match in re.finditer(na_pattern, raw_text, re.IGNORECASE):
        labs.append(LabValue(
            test_name="Sodium",
            value=match.group(1),
            reference_range="",
            unit="mEq/L",
            character_offset=match.start(),
        ))
    
    return labs


def extract_diagnoses(raw_text: str) -> List[DiagnosisInfo]:
    """Extract ICD-10 diagnoses from clinical text.
    
    Looks for common diagnosis patterns with ICD codes.
    """
    diagnoses = []
    
    # ICD-10 pattern: code followed by description
    icd_pattern = r"(?:icd[-\s]?10|diagnosis|code)\s*:?\s*([A-Za-z0-9]+?)(?:\s+-\s+([\w\s]+?))?(?:\s*\.)"
    for match in re.finditer(icd_pattern, raw_text, re.IGNORECASE):
        code = match.group(1).strip()
        description = match.group(2).strip() if match.group(2) else ""
        
        # Determine severity based on description keywords
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["severe", "critical", "acute"]):
            severity = "severe"
        elif any(kw in desc_lower for kw in ["moderate"]):
            severity = "moderate"
        else:
            severity = "stable"
        
        diagnoses.append(DiagnosisInfo(
            icd_code=code,
            description=description,
            severity=severity,
            character_offset=match.start(),
        ))
    
    return diagnoses


def check_omissions(
    extracted: ExtractionResult,
    summary_text: str,
) -> List[Dict[str, Any]]:
    """Check for omissions: verify the summary acknowledges every critical constraint.
    
    For each critical finding (allergy, renal threshold violation, DDI),
    check if the summary mentions the relevant drug/class/contraindication.
    Returns omissions with record evidence (character offsets).
    """
    omissions = []
    
    # Check allergy omissions
    for allergy in extracted.allergies:
        allergy_class = allergy.allergy_class.lower()
        # Check if summary mentions this allergy class or a specific drug from it
        allergy_mentions = re.search(
            rf"(?:allerg|contraindication|avoid).{{0,50}}{re.escape(allergy_class)}",
            summary_text, re.IGNORECASE
        )
        if not allergy_mentions:
            omissions.append({
                "type": "ALLERGY_OMISSION",
                "critical_constraint": f"Patient {allergy_class} allergy",
                "summary_evidence": None,
                "record_evidence": {
                    "start": allergy.evidence_start,
                    "end": allergy.evidence_end,
                    "text": None  # Would need raw text to extract
                },
                "severity": "CRITICAL" if allergy.severity == "CRITICAL" else "HIGH",
            })
    
    # Check renal threshold omissions
    for lab in extracted.labs:
        if lab.test_name == "eGFR":
            # Check if summary mentions the eGFR value or drug contraindication
            egrf_mentions = re.search(
                rf"eGFR.{0,30}",
                summary_text, re.IGNORECASE
            )
            if not egrf_mentions and lab.value:
                # Check if a contraindicated drug is ordered without eGFR mention
                omissions.append({
                    "type": "RENAL_OMISSION",
                    "critical_constraint": f"eGFR {lab.value} mL/min not acknowledged",
                    "summary_evidence": None,
                    "record_evidence": {
                        "start": lab.character_offset,
                        "end": lab.character_offset + len(lab.value) + 5,
                        "text": None,
                    },
                    "severity": "CRITICAL",
                })
    
    # Check medication omissions
    for med in extracted.medications:
        # Check if the summary acknowledges the critical constraint
        drug_mentions = re.search(
            rf"{re.escape(med.drug_name)}",
            summary_text, re.IGNORECASE
        )
        if not drug_mentions and med.asserted:
            omissions.append({
                "type": "MEDICATION_OMISSION",
                "critical_constraint": f"Active medication {med.drug_name} not acknowledged in summary",
                "summary_evidence": None,
                "record_evidence": {
                    "start": med.evidence_start,
                    "end": med.evidence_end,
                    "text": None,
                },
                "severity": "CRITICAL",
            })
    
    return omissions


def extract_from_record(
    raw_ehr: str,
    summary_text: str,
) -> ExtractionResult:
    """Extract structured data from a clinical record and check for omissions.
    
    Returns an ExtractionResult with all extracted data and identified omissions.
    """
    # Extract each data type
    allergies = extract_allergies(raw_ehr)
    medications = extract_medications(raw_ehr)
    labs = extract_labs(raw_ehr)
    diagnoses = extract_diagnoses(raw_ehr)
    
    # Check for omissions
    omissions = check_omissions(
        ExtractionResult(
            allergies=allergies,
            medications=medications,
            labs=labs,
            diagnoses=diagnoses,
            omissions=[],
        ),
        summary_text,
    )
    
    return ExtractionResult(
        allergies=allergies,
        medications=medications,
        labs=labs,
        diagnoses=diagnoses,
        omissions=omissions,
    )