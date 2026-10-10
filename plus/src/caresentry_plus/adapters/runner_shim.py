"""Adapter shim for Track A ModelRunner.

This is the ONLY file in Track B that touches harness.model_runner.
Complies with Contract C-05.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("caresentry_plus.adapters.runner")


@dataclass
class ForwardTelemetryDTO:
    """Decoupled Data Transfer Object for forward pass telemetry."""
    tokens: List[str]
    seq_len: int
    num_layers: int
    num_heads: int
    is_simulated: bool
    raw_telemetry: Optional[Any] = None


class ModelRunnerShim:
    """Unified wrapper around Track A ModelRunner with graceful offline fallback."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
        quantization: str = "fp16",
        device: str = "auto",
        fallback_mode: bool = False,
    ):
        self.model_id = model_id
        self.quantization = quantization
        self.device = device
        self.fallback_mode = fallback_mode
        self._runner = None

        if not fallback_mode:
            try:
                from harness.model_runner import ModelRunner
                self._runner = ModelRunner(
                    model_id=model_id,
                    quantization=quantization if quantization in ["none", "fp16", "4bit_nf4"] else "fp16",
                    device=device,
                )
            except Exception as e:
                logger.warning(
                    f"Could not initialize Track A ModelRunner ({e}). Falling back to simulation shim."
                )
                self.fallback_mode = True

    def tokenize(self, prompt: str) -> Tuple[Any, List[str]]:
        """Tokenize prompt text."""
        if self._runner is not None and not self.fallback_mode:
            try:
                return self._runner.tokenize(prompt)
            except Exception as e:
                logger.warning(f"Runner tokenize failed ({e}); falling back.")

        import re
        tokens = re.findall(r"\w+|[^\w\s]", prompt, re.UNICODE)
        return None, tokens

    def forward(
        self,
        prompt: str,
        needle: Optional[str] = None,
        is_pinned: bool = False,
        is_recency_reordered: bool = False,
    ) -> ForwardTelemetryDTO:
        """Execute forward pass and return decoupled telemetry."""
        if self._runner is not None and not self.fallback_mode:
            try:
                t = self._runner.forward(
                    prompt,
                    needle=needle,
                    is_pinned=is_pinned,
                    is_recency_reordered=is_recency_reordered,
                )
                return ForwardTelemetryDTO(
                    tokens=t.tokens,
                    seq_len=t.seq_len,
                    num_layers=t.num_layers,
                    num_heads=t.num_heads,
                    is_simulated=getattr(t, "is_simulated", False),
                    raw_telemetry=t,
                )
            except Exception as e:
                logger.warning(f"Runner forward pass failed ({e}); using fallback.")

        _, tokens = self.tokenize(prompt)
        return ForwardTelemetryDTO(
            tokens=tokens,
            seq_len=len(tokens),
            num_layers=28,
            num_heads=16,
            is_simulated=True,
            raw_telemetry=None,
        )

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.0,
    ) -> str:
        """Generate response given prompt."""
        if self._runner is not None and not self.fallback_mode:
            try:
                return self._runner.generate(
                    prompt=prompt,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
            except Exception as e:
                logger.warning(f"Runner generate failed ({e}); using fallback.")

        return f"[Simulated Output for {self.model_id}]: Summary generated without active model weights."
