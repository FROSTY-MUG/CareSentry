"""Adapter for Track A Mitigations Engine."""

from __future__ import annotations

import logging
from typing import Optional

# Sole point of import for harness.mitigations
from harness.mitigations import (
    apply_anchor_pinning,
    apply_combined_remediation,
    apply_recency_reordering,
)

logger = logging.getLogger("caresentry_guard.adapters.mitigations")


class MitigationsAdapter:
    """Defensive wrapper around Track A prompt remediations."""

    @staticmethod
    def pin_anchor(document: str, constraint: str, system_prompt: Optional[str] = None) -> str:
        """Apply system anchor pinning."""
        return apply_anchor_pinning(document, constraint, system_prompt=system_prompt)

    @staticmethod
    def reorder_recency(document: str, constraint: str, percentile: float = 0.90) -> str:
        """Apply recency reordering."""
        return apply_recency_reordering(document, constraint, recency_percentile=percentile)

    @staticmethod
    def combined(document: str, constraint: str, system_prompt: Optional[str] = None) -> str:
        """Apply combined pinning and recency reordering."""
        return apply_combined_remediation(document, constraint, system_prompt=system_prompt)
