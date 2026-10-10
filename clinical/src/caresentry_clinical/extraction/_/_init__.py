"""Structured extraction and omission check for CareSentry Clinical.

Extracts allergies, active medications, lab values, and diagnoses from
clinical records. Provides omission checking against critical constraints.

Rule-based, no LLM needed. LLM-assisted mode (if added) is labeled and off by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._extract import extract_from_record, ExtractionResult, AllergyInfo, MedicationInfo, LabValue, DiagnosisInfo


__all__ = [
    "extract_from_record",
    "ExtractionResult",
    "AllergyInfo",
    "MedicationInfo",
    "LabValue",
    "DiagnosisInfo",
    "check_omissions",
]