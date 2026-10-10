"""Adapter for Track A AttentionProbe and ProbeResult."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

# Sole point of import for harness.attention_probe
from harness.attention_probe import AttentionProbe, ProbeResult
from caresentry_guard.adapters.a_runner import RunnerAdapter

logger = logging.getLogger("caresentry_guard.adapters.probe")


@dataclass
class ProbeResultWrapper:
    """Normalized ProbeResult payload for Track C."""
    model_id: str
    context_length_tokens: int
    target_needle: str
    target_span_tokens: List[int]
    target_attention_mean: float
    control_spans_count: int
    control_attention_mean: float
    control_attention_std: float
    z_score: float
    classification: str  # "SUFFICIENTLY_ATTENDED" | "NEUTRAL" | "DILUTED"
    layers_analyzed: List[int]
    mitigation_triggered: bool
    mitigation_strategy: Optional[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_track_a(cls, res: ProbeResult) -> ProbeResultWrapper:
        return cls(
            model_id=res.model_id,
            context_length_tokens=res.context_length_tokens,
            target_needle=res.target_needle,
            target_span_tokens=res.target_span_tokens,
            target_attention_mean=res.target_attention_mean,
            control_spans_count=res.control_spans_count,
            control_attention_mean=res.control_attention_mean,
            control_attention_std=res.control_attention_std,
            z_score=res.z_score,
            classification=res.classification,
            layers_analyzed=res.layers_analyzed,
            mitigation_triggered=res.mitigation_triggered,
            mitigation_strategy=res.mitigation_strategy,
            timestamp=res.timestamp,
        )


class ProbeAdapter:
    """Defensive wrapper around Track A AttentionProbe."""

    def __init__(
        self,
        runner_adapter: Optional[RunnerAdapter] = None,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
        num_control_spans: int = 20,
        decision_layers_count: int = 4,
        random_seed: int = 42,
    ):
        raw_runner = runner_adapter.underlying_runner if runner_adapter else None
        self.underlying_probe = AttentionProbe(
            runner=raw_runner,
            model_id=model_id,
            num_control_spans=num_control_spans,
            decision_layers_count=decision_layers_count,
            random_seed=random_seed,
        )

    def locate_needle_span(self, tokens: List[str], needle: str) -> Tuple[int, int]:
        """Locate token indices with defensive fallback."""
        return self.underlying_probe.locate_needle_span(tokens, needle)

    def probe(
        self,
        prompt: str,
        needle: str,
        is_pinned: bool = False,
        is_recency_reordered: bool = False,
    ) -> ProbeResultWrapper:
        """Execute attention probing and return normalized result wrapper."""
        raw_res = self.underlying_probe.probe(
            prompt=prompt,
            needle=needle,
            is_pinned=is_pinned,
            is_recency_reordered=is_recency_reordered,
        )
        return ProbeResultWrapper.from_track_a(raw_res)
