"""CareSentry-AI Prompt Remediation & Context Re-anchoring Engine.

Implements FR-04:
- System Anchor Pinning (elevates negative constraint to terminal system prompt)
- Recency Reordering (relocates middle-depth constraint into the final 10% recency zone)
- Combined Remediation for ultra-dense (>16k token) geriatric records.
"""

from __future__ import annotations

import enum
import re
from typing import Optional, Tuple


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
) -> str:
    """Combined Remediation: Both anchors the constraint into system prompts

    AND reorders into the final recency zone for maximum attention retention.
    """
    reordered = apply_recency_reordering(document, constraint)
    pinned = apply_anchor_pinning(reordered, constraint, system_prompt=system_prompt)
    return pinned
