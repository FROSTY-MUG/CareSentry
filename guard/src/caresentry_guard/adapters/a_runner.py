"""Adapter for Track A ModelRunner and ForwardPassTelemetry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import torch

# Sole point of import for harness.model_runner
from harness.model_runner import ForwardPassTelemetry, ModelRunner

logger = logging.getLogger("caresentry_guard.adapters.runner")


@dataclass
class TelemetryWrapper:
    """Normalized telemetry contract for Track C consumers."""
    input_ids: torch.Tensor
    tokens: List[str]
    seq_len: int
    num_layers: int
    num_heads: int
    attentions: Tuple[Any, ...]
    is_simulated: bool

    @classmethod
    def from_track_a(cls, tel: ForwardPassTelemetry) -> TelemetryWrapper:
        return cls(
            input_ids=tel.input_ids,
            tokens=tel.tokens,
            seq_len=tel.seq_len,
            num_layers=tel.num_layers,
            num_heads=tel.num_heads,
            attentions=tel.attentions,
            is_simulated=tel.is_simulated,
        )


class RunnerAdapter:
    """Defensive wrapper around Track A ModelRunner."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
        device: str = "auto",
        quantization: str = "none",
        force_simulation: bool = False,
    ):
        self.model_id = model_id
        self.underlying_runner = ModelRunner(
            model_id=model_id,
            device=device,
            quantization=quantization,
            force_simulation=force_simulation,
        )

    @property
    def is_loaded(self) -> bool:
        return bool(self.underlying_runner.is_loaded)

    @property
    def model(self) -> Any:
        return self.underlying_runner.model

    @property
    def tokenizer(self) -> Any:
        return self.underlying_runner.tokenizer

    def tokenize(self, prompt: str) -> Tuple[torch.Tensor, List[str]]:
        """Extract input IDs and tokens with safe fallback."""
        return self.underlying_runner.tokenize(prompt)

    def forward(
        self,
        prompt: str,
        needle: Optional[str] = None,
        is_pinned: bool = False,
        is_recency_reordered: bool = False,
    ) -> TelemetryWrapper:
        """Execute forward pass and return normalized telemetry."""
        raw_telemetry = self.underlying_runner.forward(
            prompt=prompt,
            needle=needle,
            is_pinned=is_pinned,
            is_recency_reordered=is_recency_reordered,
        )
        return TelemetryWrapper.from_track_a(raw_telemetry)
