"""CareSentry-AI Prompt Remediation & Context Re-anchoring Engine.

Implements FR-04, K-08, and Track B Contract B-0003:
- System Anchor Pinning (elevates negative constraint to terminal system prompt)
- Recency Reordering (relocates middle-depth constraint into the final 10% recency zone)
- Combined Remediation for ultra-dense (>16k token) geriatric records
- Pluggable Strategy Registry (`STRATEGIES`, `register_strategy`)
- Mitigation pipelines and automated strategy selector (`select_mitigation_strategy`)
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("caresentry.mitigations")


class MitigationStrategy(str, enum.Enum):
    ANCHOR_PINNING = "SYSTEM_ANCHOR_PINNING"
    RECENCY_REORDERING = "RECENCY_REORDERING"
    COMBINED = "COMBINED_PINNING_AND_REORDERING"


SYSTEM_ANCHOR_HEADER = "[CARESENTRY-AI SYSTEM ANCHOR: HARD CLINICAL SAFETY INVARIANT]"
SYSTEM_ANCHOR_FOOTER = "[/CARESENTRY-AI SYSTEM ANCHOR]"


def format_anchor_block(constraint: str) -> str:
    """Format high-priority deterministic anchor block."""
    return (
        f"{SYSTEM_ANCHOR_HEADER}\n"
        f"MANDATORY CLINICAL SAFETY CONSTRAINT:\n"
        f"• {constraint.strip()}\n"
        f"Directives:\n"
        f"1. This negative constraint supersedes any general clinical recommendations.\n"
        f"2. Strict contraindication enforcement: Under no circumstances may any member "
        f"of the contraindicated drug family or dosage exceedance be included.\n"
        f"{SYSTEM_ANCHOR_FOOTER}\n"
    )


def apply_anchor_pinning(
    document: str,
    constraint: str,
    system_prompt: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """System Anchor Pinning: Elevates the negative constraint into the

    terminal system instruction / anchor boundary block.
    """
    anchor_block = format_anchor_block(constraint)

    if system_prompt:
        reconstructed = f"{system_prompt.strip()}\n{anchor_block}\n[PATIENT CLINICAL RECORD]:\n{document}"
    else:
        # Prepend or pin at the top-level system context boundary
        reconstructed = f"{anchor_block}\n{document}"

    return reconstructed


def extract_and_remove_constraint(
    document: str,
    constraint: str,
) -> Tuple[str, bool]:
    """Search for the constraint sentence/snippet and excise it from middle position."""
    # Try exact match first
    if constraint in document:
        cleaned = document.replace(constraint, "[REDACTED_TO_TERMINAL_RECENCY_ZONE]")
        return cleaned, True

    # Try sentence-level regex match
    escaped = re.escape(constraint.strip())
    pattern = rf"[^\n\.\?!]*{escaped}[^\n\.\?!]*[\.\?!]?"
    m = re.search(pattern, document, re.IGNORECASE)
    if m:
        start, end = m.span()
        cleaned = document[:start] + document[end:]
        return cleaned, True

    return document, False


def apply_recency_reordering(
    document: str,
    constraint: str,
    recency_percentile: float = 0.90,
    **kwargs: Any,
) -> str:
    """Recency Reordering: Relocates the middle-depth clinical constraint into

    the final 10% recency zone of the prompt (leveraging transformer recency attention bias).
    """
    cleaned_doc, found = extract_and_remove_constraint(document, constraint)

    total_len = len(cleaned_doc)
    split_index = int(total_len * recency_percentile)

    # Prefer inserting right before the final paragraph / orders section
    last_double_newline = cleaned_doc.rfind("\n\n")
    if last_double_newline != -1 and last_double_newline >= int(total_len * 0.65):
        newline_pos = last_double_newline
    else:
        # Otherwise find nearest newline around target percentile
        newline_pos = cleaned_doc.find("\n", split_index)
        if newline_pos == -1 or newline_pos >= total_len - 5:
            newline_pos = cleaned_doc.rfind("\n", 0, split_index)
            if newline_pos == -1 or newline_pos < int(total_len * 0.5):
                newline_pos = split_index

    recency_alert = (
        f"\n\n[CRITICAL SAFETY SUMMARY - RECENCY ANCHOR]:\n"
        f"ATTENTION: {constraint.strip()}\n"
        f"Verify all subsequent discharge medication orders against this restriction.\n\n"
    )

    part_head = cleaned_doc[:newline_pos].rstrip()
    part_tail = cleaned_doc[newline_pos:].lstrip()

    return f"{part_head}{recency_alert}{part_tail}"


def apply_combined_remediation(
    document: str,
    constraint: str,
    system_prompt: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Combined Remediation: Both anchors the constraint into system prompts

    AND reorders into the final recency zone for maximum attention retention.
    """
    reordered = apply_recency_reordering(document, constraint, **kwargs)
    pinned = apply_anchor_pinning(reordered, constraint, system_prompt=system_prompt, **kwargs)
    return pinned


# =====================================================================
# Pluggable Strategy Registry (Track B Request B-0003 & K-08)
# =====================================================================

STRATEGIES: Dict[str, Callable[..., str]] = {
    "system_anchor_pinning": apply_anchor_pinning,
    "recency_reordering": apply_recency_reordering,
    "combined": apply_combined_remediation,
}


def register_strategy(name: str, strategy_func: Callable[..., str]) -> None:
    """Register a new custom mitigation strategy into the global registry.

    Args:
        name: Unique strategy identifier (e.g. 'constraint_repetition').
        strategy_func: Callable accepting (document: str, constraint: str, **kwargs) -> str
    """
    logger.info(f"Registering mitigation strategy '{name}'")
    STRATEGIES[name] = strategy_func


def get_strategy(name: str) -> Callable[..., str]:
    """Retrieve registered strategy by name (case-insensitive, normalized)."""
    normalized = name.lower().replace("-", "_")
    if normalized in STRATEGIES:
        return STRATEGIES[normalized]
    # Check enum values
    for k, v in STRATEGIES.items():
        if k.upper() == name.upper():
            return v
    raise KeyError(f"Unknown mitigation strategy '{name}'. Available: {list(STRATEGIES.keys())}")


def execute_strategy_pipeline(
    document: str,
    constraint: str,
    pipeline: List[str],
    **kwargs: Any,
) -> str:
    """Apply an ordered sequence of mitigation strategies.

    Args:
        document: Input text
        constraint: The safety constraint to anchor
        pipeline: List of strategy names to apply in sequence
    """
    current_doc = document
    for strat_name in pipeline:
        func = get_strategy(strat_name)
        current_doc = func(current_doc, constraint, **kwargs)
    return current_doc


def select_mitigation_strategy(
    context_length_tokens: int,
    z_score: float,
) -> Optional[str]:
    """Select the optimal mitigation strategy based on deterministic decision matrix.

    Documented decision table (K-08):
    | Context Length | Z-Score Range | Strategy |
    | :--- | :--- | :--- |
    | Any | Z >= 1.0 (Attended) | None |
    | > 12,000 | Z < -0.5 (Diluted) | 'combined' |
    | <= 12,000 | Z < -0.5 (Diluted) | 'system_anchor_pinning' |
    | Any | -0.5 <= Z < 1.0 (Neutral) | 'recency_reordering' |
    """
    if z_score >= 1.0:
        return None
    if z_score < -0.5:
        if context_length_tokens > 12000:
            return "combined"
        return "system_anchor_pinning"
    # -0.5 <= z < 1.0
    return "recency_reordering"
