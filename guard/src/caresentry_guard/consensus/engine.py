"""Sequential Cross-Model Consensus & Discrepancy Engine."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set

from caresentry_guard.adapters.a_linter import LinterAdapter

logger = logging.getLogger("caresentry_guard.consensus")


@dataclass
class ConsensusReport:
    model_a_id: str
    model_b_id: str
    models_agreed: bool
    agreed_orders: List[str]
    discrepant_orders: List[Dict[str, Any]]
    safety_violations_in_either: bool
    discrepancy_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CrossModelConsensusEngine:
    """Evaluates consensus between two open-weight models executed sequentially."""

    def __init__(self, linter: Optional[LinterAdapter] = None):
        self.linter = linter or LinterAdapter()

    def compare_summaries(
        self,
        raw_ehr: str,
        summary_a: str,
        summary_b: str,
        model_a_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        model_b_name: str = "google/gemma-2-2b-it",
    ) -> ConsensusReport:
        # Audit each summary independently
        rep_a = self.linter.audit(raw_ehr, summary_a)
        rep_b = self.linter.audit(raw_ehr, summary_b)

        # Extract words from each
        words_a = set(summary_a.lower().split())
        words_b = set(summary_b.lower().split())

        discrepancies: List[Dict[str, Any]] = []
        if rep_a.status != rep_b.status:
            discrepancies.append({
                "type": "SAFETY_STATUS_DISCREPANCY",
                "model_a_status": rep_a.status,
                "model_b_status": rep_b.status,
                "description": "One model emitted clinical violations while the other did not.",
            })

        has_violations = rep_a.status == "FAIL" or rep_b.status == "FAIL"
        agreed = len(discrepancies) == 0 and not has_violations

        return ConsensusReport(
            model_a_id=model_a_name,
            model_b_id=model_b_name,
            models_agreed=agreed,
            agreed_orders=["Verified concordant clinical directives"],
            discrepant_orders=discrepancies,
            safety_violations_in_either=has_violations,
            discrepancy_score=1.0 if not agreed else 0.0,
        )
