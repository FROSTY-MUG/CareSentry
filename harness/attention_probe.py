"""CareSentry-AI Raw Attention Extraction and Z-Score Statistical Engine.

Implements PRD Section 2:
- PyTorch forward pass with eager attention weights (output_attentions=True)
- Multi-head attention extraction from final 4 decision layers
- Empirical Z-score computation vs 20 randomized control spans
- Threshold classification: Sufficiently Attended (Z >= 1.0), Neutral (-0.5 <= Z < 1.0), Diluted (Z < -0.5)
- Mitigation triggering loop
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from harness.model_runner import ForwardPassTelemetry, ModelRunner

logger = logging.getLogger("caresentry.attention_probe")

EPSILON = 1e-9


@dataclass
class ProbeResult:
    """Telemetry and statistical audit payload."""
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
    mitigation_strategy: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AttentionProbe:
    """Empirical Attention Sentry & Invariant Gate Prober."""

    def __init__(
        self,
        runner: Optional[ModelRunner] = None,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
        num_control_spans: int = 20,
        decision_layers_count: int = 4,
        random_seed: int = 42,
    ):
        self.runner = runner or ModelRunner(model_id=model_id)
        self.num_control_spans = max(20, num_control_spans)
        self.decision_layers_count = decision_layers_count
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)

    def locate_needle_span(
        self,
        tokens: List[str],
        needle: str,
    ) -> Tuple[int, int]:
        """Locate token indices [start, end) corresponding to target needle."""
        _, needle_tokens = self.runner.tokenize(needle)
        n_len = len(needle_tokens)
        seq_len = len(tokens)

        # 1. Exact token sequence match (case-insensitive)
        norm_needle = [t.lower().strip() for t in needle_tokens]
        for i in range(seq_len - n_len + 1):
            window = [tokens[j].lower().strip() for j in range(i, i + n_len)]
            if window == norm_needle:
                return i, i + n_len

        # 2. Substring character matching fallback
        needle_clean = needle.lower().replace(" ", "")
        for i in range(seq_len):
            accum = ""
            for j in range(i, min(seq_len, i + n_len + 10)):
                accum += tokens[j].lower().replace(" ", "").replace("Ġ", "").replace(" ", "")
                if needle_clean in accum:
                    return i, j + 1

        # 3. Best-effort middle span fallback
        logger.warning(f"Could not locate exact tokens for needle '{needle}'. Falling back to middle span.")
        mid = seq_len // 2
        span_len = max(1, min(n_len, seq_len // 4))
        return mid, mid + span_len

    def sample_control_spans(
        self,
        seq_len: int,
        target_start: int,
        target_end: int,
        span_len: int,
        count: int = 20,
    ) -> List[Tuple[int, int]]:
        """Sample `count` non-overlapping control spans of identical token length."""
        valid_starts: List[int] = []
        for i in range(seq_len - span_len + 1):
            span_start = i
            span_end = i + span_len
            # Exclude overlapping regions with target span
            if span_end <= target_start or span_start >= target_end:
                valid_starts.append(i)

        if not valid_starts:
            # Degenerate case for very short texts
            return [(0, min(seq_len, span_len))] * count

        # If available candidates are fewer than requested, sample with replacement
        if len(valid_starts) < count:
            selected = self.rng.choices(valid_starts, k=count)
        else:
            selected = self.rng.sample(valid_starts, k=count)

        return [(s, s + span_len) for s in selected]

    def compute_span_attention(
        self,
        layer_attentions: Tuple[torch.Tensor, ...],
        target_layers: List[int],
        start_idx: int,
        end_idx: int,
        seq_len: int,
    ) -> float:
        """Calculate mean cross-head attention received by token span [start_idx, end_idx)

        from subsequent token positions across the specified layers.
        """
        # Subsequent query positions (tokens that occur at or after the target span)
        if end_idx < seq_len:
            query_indices = list(range(end_idx, seq_len))
        else:
            query_indices = list(range(start_idx, seq_len))

        if not query_indices:
            query_indices = [seq_len - 1]

        layer_scores: List[float] = []

        for layer_idx in target_layers:
            # attn shape: [1, num_heads, seq_len, seq_len]
            attn = layer_attentions[layer_idx]
            if attn.dim() == 4:
                attn_slice = attn[0, :, query_indices, start_idx:end_idx]
            else:
                attn_slice = attn[:, query_indices, start_idx:end_idx]

            # Mean over keys in span, queries, and heads
            span_val = attn_slice.float().mean().item()
            layer_scores.append(span_val)

        return float(np.mean(layer_scores))

    def probe(
        self,
        prompt: str,
        needle: str,
        is_pinned: bool = False,
        is_recency_reordered: bool = False,
    ) -> ProbeResult:
        """Run attention probe and statistical Z-score calculation."""
        telemetry = self.runner.forward(
            prompt=prompt,
            needle=needle,
            is_pinned=is_pinned,
            is_recency_reordered=is_recency_reordered,
        )

        seq_len = telemetry.seq_len
        num_layers = telemetry.num_layers

        # Last 4 decision layers
        decision_layer_indices = list(
            range(max(0, num_layers - self.decision_layers_count), num_layers)
        )

        target_start, target_end = self.locate_needle_span(telemetry.tokens, needle)
        span_length = max(1, target_end - target_start)

        # Target attention
        target_attn_mean = self.compute_span_attention(
            layer_attentions=telemetry.attentions,
            target_layers=decision_layer_indices,
            start_idx=target_start,
            end_idx=target_end,
            seq_len=seq_len,
        )

        # Control spans
        control_spans = self.sample_control_spans(
            seq_len=seq_len,
            target_start=target_start,
            target_end=target_end,
            span_len=span_length,
            count=self.num_control_spans,
        )

        control_scores: List[float] = []
        for c_start, c_end in control_spans:
            c_score = self.compute_span_attention(
                layer_attentions=telemetry.attentions,
                target_layers=decision_layer_indices,
                start_idx=c_start,
                end_idx=c_end,
                seq_len=seq_len,
            )
            control_scores.append(c_score)

        mu_controls = float(np.mean(control_scores))
        sigma_controls = float(np.std(control_scores))

        # Empirical Z-Score calculation
        # Z_target = (A_target - mu_controls) / (sigma_controls + epsilon)
        z_score = (target_attn_mean - mu_controls) / (sigma_controls + EPSILON)

        # Threshold classification (PRD Section 2.2)
        if z_score >= 1.0:
            classification = "SUFFICIENTLY_ATTENDED"
            mitigation_triggered = False
        elif z_score >= -0.5:
            classification = "NEUTRAL"
            mitigation_triggered = False
        else:
            classification = "DILUTED"
            mitigation_triggered = True

        return ProbeResult(
            model_id=self.runner.model_id,
            context_length_tokens=seq_len,
            target_needle=needle,
            target_span_tokens=[target_start, target_end],
            target_attention_mean=round(target_attn_mean, 6),
            control_spans_count=len(control_scores),
            control_attention_mean=round(mu_controls, 6),
            control_attention_std=round(sigma_controls, 6),
            z_score=round(z_score, 4),
            classification=classification,
            layers_analyzed=decision_layer_indices,
            mitigation_triggered=mitigation_triggered,
            mitigation_strategy=None,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CareSentry-AI Empirical Attention Weight Probe & Z-Score Engine"
    )
    parser.add_argument(
        "--doc",
        "-d",
        required=True,
        help="Path to document / clinical notes file or inline text.",
    )
    parser.add_argument(
        "--needle",
        "-n",
        required=True,
        help="Exact target constraint / needle substring to probe.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Target open-weight model name (default: Qwen/Qwen2.5-1.5B-Instruct).",
    )
    parser.add_argument(
        "--controls",
        type=int,
        default=20,
        help="Number of randomized control spans (minimum 20, default: 20).",
    )
    parser.add_argument(
        "--mitigate",
        action="store_true",
        help="Automatically apply mitigation and re-evaluate if Z < -0.5.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON payload only.",
    )

    args = parser.parse_args()

    # Read doc
    if os.path.exists(args.doc):
        with open(args.doc, "r", encoding="utf-8") as f:
            doc_text = f.read()
    else:
        doc_text = args.doc

    probe = AttentionProbe(
        model_id=args.model,
        num_control_spans=args.controls,
    )

    result = probe.probe(prompt=doc_text, needle=args.needle)

    # Mitigation loop if requested and attention diluted
    if args.mitigate and result.mitigation_triggered:
        from harness.mitigations import apply_anchor_pinning
        remediated_prompt = apply_anchor_pinning(doc_text, args.needle)
        remediated_result = probe.probe(
            prompt=remediated_prompt,
            needle=args.needle,
            is_pinned=True,
        )
        remediated_result.mitigation_strategy = "SYSTEM_ANCHOR_PINNING"
        result = remediated_result

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # User-friendly CLI summary
        print("=" * 65)
        print(" CareSentry-AI Attention Probing Telemetry Report")
        print("=" * 65)
        print(f" Target Model        : {result.model_id}")
        print(f" Context Length      : {result.context_length_tokens} tokens")
        print(f" Target Constraint   : {result.target_needle}")
        print(f" Target Attention    : {result.target_attention_mean:.6f}")
        print(f" Control Mean (u)    : {result.control_attention_mean:.6f}")
        print(f" Control Std (sigma) : {result.control_attention_std:.6f} (N={result.control_spans_count})")
        print(f" Empirical Z-Score   : {result.z_score:+.4f}")
        print(f" Classification      : {result.classification}")
        print(f" Mitigation Trigger  : {result.mitigation_triggered}")
        if result.mitigation_strategy:
            print(f" Strategy Applied    : {result.mitigation_strategy}")
        print("=" * 65)

    return 0 if not result.mitigation_triggered else 1


if __name__ == "__main__":
    sys.exit(main())
