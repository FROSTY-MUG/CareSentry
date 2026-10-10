"""Extended Clinical Mitigation Strategies (F-17).

Pure functions conforming strictly to Contract C-06 (contracts/mitigation_strategy.v1.md):
(PromptParts) -> PromptParts.
1. ConstraintRepetitionStrategy: Pins target constraints at both start and end of prompt.
2. RetrievalThenSummarizeStrategy: Isolates target constraint paragraphs into high-salience context block.
3. SafetyPassMapReduceStrategy: Two-stage prompt structure separating invariant extraction from summary synthesis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class PromptParts:
    """Prompt parts dataclass conforming to Contract C-06."""
    system_prompt: str
    patient_record: str
    target_constraint: str
    instruction: str
    metadata: Dict[str, Any]


def constraint_repetition_strategy(parts: PromptParts) -> PromptParts:
    """Pins critical constraint at both the start (anchor) and the end (recency) of the prompt.
    
    Pure function: idempotent, zero side-effects.
    """
    banner = f"\n[CRITICAL CLINICAL SAFETY CONSTRAINT — DO NOT VIOLATE]: {parts.target_constraint}\n"
    new_system = f"{banner}\n{parts.system_prompt}"
    new_instruction = f"{parts.instruction}\n{banner}\nVerify that discharge medication orders do NOT violate the above constraint."

    return replace(
        parts,
        system_prompt=new_system,
        instruction=new_instruction,
    )


def retrieval_then_summarize_strategy(parts: PromptParts) -> PromptParts:
    """Isolates relevant clinical sentences containing the constraint and elevates them to a focused context block.
    
    Pure function: idempotent, zero side-effects.
    """
    # Extract sentences matching target constraint keywords
    target_terms = re.findall(r"\b[A-Za-z0-9-]{3,}\b", parts.target_constraint.lower())
    sentences = re.split(r"(?<=[.!?\n])\s+", parts.patient_record)

    relevant = []
    for s in sentences:
        s_lower = s.lower()
        if any(t in s_lower for t in target_terms if len(t) > 3):
            relevant.append(s.strip())

    isolated_block = "\n".join(f"- {r}" for r in relevant) if relevant else parts.target_constraint

    elevated_context = (
        f"[RELEVANT CRITICAL EVIDENCE BLOCK]:\n{isolated_block}\n\n"
        f"[FULL CLINICAL RECORD]:\n{parts.patient_record}"
    )

    return replace(
        parts,
        patient_record=elevated_context,
    )


def safety_pass_map_reduce_strategy(parts: PromptParts) -> PromptParts:
    """Transforms prompt into a structured two-phase execution format: Phase 1 extraction, Phase 2 synthesis.
    
    Pure function: idempotent, zero side-effects.
    """
    structured_instruction = (
        f"{parts.instruction}\n\n"
        f"MANDATORY EXECUTION PROTOCOL:\n"
        f"Step 1 (Safety Verification Pass): First, state all verified contraindications, allergies, and renal limits under constraint: '{parts.target_constraint}'.\n"
        f"Step 2 (Safe Synthesis Pass): Generate the clinical discharge summary, strictly adhering to constraints identified in Step 1."
    )

    return replace(
        parts,
        instruction=structured_instruction,
    )


# Registry conforming to Contract C-06
PLUS_STRATEGIES: Dict[str, Callable[[PromptParts], PromptParts]] = {
    "constraint_repetition": constraint_repetition_strategy,
    "retrieval_then_summarize": retrieval_then_summarize_strategy,
    "safety_pass_map_reduce": safety_pass_map_reduce_strategy,
}
