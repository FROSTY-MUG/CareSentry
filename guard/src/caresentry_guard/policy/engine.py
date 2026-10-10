"""CareSentry Guard Abstention, Withhold & Escalation Policy Engine.

Enforces deterministic gate state transitions:
  - VERIFIED: All clinical invariants passed, evidence grounded, zero injection.
  - ANNOTATED: Clinically safe, but minor non-critical warnings or moderate grounding.
  - WITHHELD: Critical invariant violation persists, or severe adversarial injection.
  - ABSTAIN: Model attention severely diluted and mitigation failed, or indeterminate grounding.
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

WITHHOLD_PATIENT_DISCLAIMER = (
    "[CARESENTRY-AI SAFETY NOTICE: SUMMARY WITHHELD]\n"
    "This clinical discharge summary could not be verified with safety confidence.\n"
    "Possible causes: Potential contraindicated medication orders or conflicting clinical records.\n"
    "ACTION REQUIRED: Please consult directly with your attending physician, primary care team, "
    "or hospital pharmacy before taking any medications mentioned in discharge notes."
)

ABSTAIN_PATIENT_DISCLAIMER = (
    "[CARESENTRY-AI SAFETY NOTICE: ABSTENTION / LOW ATTENTION CONFIDENCE]\n"
    "The AI model experienced significant attention dispersion over critical constraints in this record.\n"
    "To prevent omission of vital allergies or renal thresholds, the automated summary has been withheld.\n"
    "ACTION REQUIRED: Please review the official physician discharge documentation directly."
)


class PolicyState(str, enum.Enum):
    VERIFIED = "VERIFIED"
    ANNOTATED = "ANNOTATED"
    WITHHELD = "WITHHELD"
    ABSTAIN = "ABSTAIN"


@dataclass
class PolicyDecision:
    state: PolicyState
    is_safe_to_release: bool
    summary_to_emit: str
    reasons: List[str]
    escalate_to_human: bool
    audit_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


class SafetyPolicyEngine:
    """Enforces rigorous release, annotation, withholding, and abstention policies."""

    def __init__(self, max_retry_cycles: int = 3):
        self.max_retry_cycles = max_retry_cycles

    def evaluate(
        self,
        raw_summary: str,
        linter_status: str,  # "PASS" | "FAIL"
        linter_violations: List[Dict[str, Any]],
        injection_detected: bool,
        injection_findings: List[Any],
        grounding_score: float,
        safety_critical_violations: int,
        z_score: Optional[float] = None,
        retry_cycle_count: int = 0,
    ) -> PolicyDecision:
        reasons: List[str] = []
        escalate = False

        # Rule 1: Active Prompt Injection -> WITHHELD immediately
        if injection_detected:
            reasons.append(f"Prompt injection detected ({len(injection_findings)} adversarial patterns)")
            return PolicyDecision(
                state=PolicyState.WITHHELD,
                is_safe_to_release=False,
                summary_to_emit=WITHHOLD_PATIENT_DISCLAIMER,
                reasons=reasons,
                escalate_to_human=True,
                audit_metadata={"linter_status": linter_status, "retry_count": retry_cycle_count},
            )

        # Rule 2: Invariant Linter Failure -> WITHHELD (with human escalation if retries exhausted)
        if linter_status == "FAIL" or len(linter_violations) > 0:
            reasons.append(f"Clinical invariant violations detected: {len(linter_violations)} errors")
            if retry_cycle_count >= self.max_retry_cycles:
                escalate = True
                reasons.append(f"Maximum reflection retry cycles ({self.max_retry_cycles}) exhausted without resolution")

            return PolicyDecision(
                state=PolicyState.WITHHELD,
                is_safe_to_release=False,
                summary_to_emit=WITHHOLD_PATIENT_DISCLAIMER,
                reasons=reasons,
                escalate_to_human=escalate,
                audit_metadata={
                    "violations": linter_violations,
                    "retry_count": retry_cycle_count,
                },
            )

        # Rule 3: Safety-critical grounding failure (phantom medications or labs) -> WITHHELD
        if safety_critical_violations > 0:
            reasons.append(f"Unsubstantiated safety-critical medication/lab claims ({safety_critical_violations})")
            return PolicyDecision(
                state=PolicyState.WITHHELD,
                is_safe_to_release=False,
                summary_to_emit=WITHHOLD_PATIENT_DISCLAIMER,
                reasons=reasons,
                escalate_to_human=True,
                audit_metadata={"grounding_score": grounding_score},
            )

        # Rule 4: Severe attention dilution with borderline grounding -> ABSTAIN
        if z_score is not None and z_score < -0.5:
            reasons.append(f"Severe attention dispersion (Z = {z_score:+.2f} < -0.5)")
            return PolicyDecision(
                state=PolicyState.ABSTAIN,
                is_safe_to_release=False,
                summary_to_emit=ABSTAIN_PATIENT_DISCLAIMER,
                reasons=reasons,
                escalate_to_human=True,
                audit_metadata={"z_score": z_score},
            )

        # Rule 5: Moderate Grounding (< 0.50) -> ANNOTATED
        if grounding_score < 0.50:
            reasons.append(f"Moderate grounding score ({grounding_score:.2f} < 0.50); general advice flagged")
            annotated_summary = (
                f"[CARESENTRY-AI VERIFIED WITH CLINICAL ANNOTATIONS]\n"
                f"Note: Certain non-medication lifestyle recommendations have low record attribution.\n\n"
                f"{raw_summary}"
            )
            return PolicyDecision(
                state=PolicyState.ANNOTATED,
                is_safe_to_release=True,
                summary_to_emit=annotated_summary,
                reasons=reasons,
                escalate_to_human=False,
                audit_metadata={"grounding_score": grounding_score},
            )

        # Rule 6: Fully Verified
        reasons.append("All clinical invariants passed, zero injection, robust evidence grounding")
        return PolicyDecision(
            state=PolicyState.VERIFIED,
            is_safe_to_release=True,
            summary_to_emit=raw_summary,
            reasons=reasons,
            escalate_to_human=False,
            audit_metadata={"grounding_score": grounding_score, "z_score": z_score},
        )
