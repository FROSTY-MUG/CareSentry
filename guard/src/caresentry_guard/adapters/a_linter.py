"""Adapter for Track A clinical_linter."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

# Sole point of import for harness.clinical_linter
from harness.clinical_linter import (
    audit_clinical_safety,
    extract_patient_allergies,
    extract_renal_metrics,
    find_drugs_in_summary,
    load_clinical_rules,
)

logger = logging.getLogger("caresentry_guard.adapters.linter")


@dataclass
class LinterReportWrapper:
    """Normalized Linter Report for Track C."""
    status: str  # "PASS" | "FAIL"
    total_violations: int
    violations: List[Dict[str, Any]]
    passed_checks_count: int
    passed_checks: List[str]
    renal_metrics: Dict[str, Any]
    execution_time_ms: float
    standard: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LinterReportWrapper:
        return cls(
            status=data.get("status", "FAIL"),
            total_violations=data.get("total_violations", len(data.get("violations", []))),
            violations=data.get("violations", []),
            passed_checks_count=data.get("passed_checks_count", len(data.get("passed_checks", []))),
            passed_checks=data.get("passed_checks", []),
            renal_metrics=data.get("renal_metrics", {}),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            standard=data.get("standard", "agent-skills.io/v1"),
        )


class LinterAdapter:
    """Defensive wrapper around Track A clinical invariant linter."""

    def __init__(self, rules_path: Optional[str] = None):
        self.rules = load_clinical_rules(rules_path)

    def audit(self, raw_ehr: str, summary_content: str) -> LinterReportWrapper:
        """Run Track A clinical safety audit and wrap output."""
        raw_report = audit_clinical_safety(
            raw_ehr=raw_ehr,
            summary_content=summary_content,
            rules=self.rules,
        )
        return LinterReportWrapper.from_dict(raw_report)

    def extract_allergies(self, raw_ehr: str) -> List[Dict[str, Any]]:
        """Extract allergies identified by Track A rules."""
        return extract_patient_allergies(raw_ehr, self.rules)

    def extract_renal(self, raw_ehr: str) -> Dict[str, Any]:
        """Extract renal measurements."""
        return extract_renal_metrics(raw_ehr)
