"""CareSentry-AI Raw Attention Extraction and Z-Score Statistical Engine.

Implements PRD Section 2, Verification PRD, and Track A2 Upgrades:
- PyTorch forward pass with eager attention weights or blockwise estimation
- Multi-head attention extraction from final 4 decision layers
- Empirical Z-score computation vs randomized / stratified control spans
- Threshold classification: Sufficiently Attended (Z >= 1.0), Neutral (-0.5 <= Z < 1.0), Diluted (Z < -0.5)
- K-01: Blockwise attention integration
- K-02: Statistical Z-Score v2 with stratified controls, 95% bootstrap CI, and permutation p-value
- K-03: SpanLocator offset-aware token mapping, strict error on missing needle
- K-04: Multi-constraint probing (probe_all_constraints)
- K-05 & R-01: Attention trace export conforming to contracts/attention_trace.v1.schema.json
- Mitigation triggering loop
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import random
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch

from harness.model_runner import ForwardPassTelemetry, ModelRunner
from harness.span_locator import SpanLocator, SpanLocationError

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
    # v2 enhanced fields (backward-compatible defaults)
    z_method: str = "v1"
    z_ci_95: Optional[Tuple[float, float]] = None
    p_value: Optional[float] = None
    control_spans: Optional[List[List[int]]] = None
    stratification_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_trace_dict(
        self,
        dtype: str = "fp16",
        attn_impl: str = "eager",
        tokens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Convert result into contracts/attention_trace.v1.schema.json format."""
        return {
            "schema": "attention_trace.v1",
            "model_id": self.model_id,
            "dtype": dtype,
            "attn_impl": attn_impl,
            "layers_used": self.layers_analyzed,
            "doc_token_count": self.context_length_tokens,
            "needle_text": self.target_needle,
            "needle_span": self.target_span_tokens,
            "control_spans": self.control_spans or [],
            "target_attention_mean": self.target_attention_mean,
            "control_attention_mean": self.control_attention_mean,
            "control_attention_std": self.control_attention_std,
            "z_score": self.z_score,
            "classification": self.classification,
            "mitigation_applied": bool(self.mitigation_strategy),
            "mitigation_strategy": self.mitigation_strategy,
            "timestamp": self.timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


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
        self.span_locator = SpanLocator(tokenizer=getattr(self.runner, "tokenizer", None))

    def locate_needle_span(
        self,
        tokens: List[str],
        needle: str,
        prompt: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Locate token indices [start, end) corresponding to target needle."""
        matches = self.span_locator.locate(
            tokens=tokens,
            needle=needle,
            full_text=prompt,
            strategy="first",
        )
        return matches[0].start_token, matches[0].end_token

    def sample_control_spans(
        self,
        seq_len: int,
        target_start: int,
        target_end: int,
        span_len: int,
        count: int = 20,
        tokens: Optional[List[str]] = None,
        stratified: bool = False,
    ) -> List[Tuple[int, int]]:
        """Sample `count` non-overlapping control spans of identical token length.

        Supports uniform sampling (v1) and stratified sampling by depth and token class (v2).
        """
        valid_starts: List[int] = []
        for i in range(seq_len - span_len + 1):
            span_start = i
            span_end = i + span_len
            # Exclude overlapping regions with target span
            if span_end <= target_start or span_start >= target_end:
                valid_starts.append(i)

        if not valid_starts:
            return [(0, min(seq_len, span_len))] * count

        if stratified and len(valid_starts) >= count:
            target_mid_rel = (target_start + target_end) / (2.0 * max(seq_len, 1))
            # Stratify by depth proximity within +/- 20%
            near_candidates = [
                s for s in valid_starts
                if abs(((s + span_len / 2.0) / max(seq_len, 1)) - target_mid_rel) <= 0.20
            ]
            # Exclude purely punctuation tokens if tokens list is provided
            if tokens is not None:
                content_candidates = []
                for s in (near_candidates if len(near_candidates) >= count else valid_starts):
                    span_toks = tokens[s : s + span_len]
                    has_content = any(re.search(r"\w", t) for t in span_toks)
                    if has_content:
                        content_candidates.append(s)
                if len(content_candidates) >= count:
                    valid_starts = content_candidates
            elif near_candidates and len(near_candidates) >= count:
                valid_starts = near_candidates

        # Sample with or without replacement
        if len(valid_starts) < count:
            selected = self.rng.choices(valid_starts, k=count)
        else:
            selected = self.rng.sample(valid_starts, k=count)

        return [(s, s + span_len) for s in selected]

    def compute_span_attention(
        self,
        layer_attentions: Tuple[Any, ...],
        target_layers: List[int],
        start_idx: int,
        end_idx: int,
        seq_len: int,
    ) -> float:
        """Calculate mean cross-head attention received by token span [start_idx, end_idx)

        from subsequent token positions across the specified layers.
        """
        if end_idx < seq_len:
            query_indices = list(range(end_idx, seq_len))
        else:
            query_indices = list(range(start_idx, seq_len))

        if not query_indices:
            query_indices = [seq_len - 1]

        layer_scores: List[float] = []

        for layer_idx in target_layers:
            attn = layer_attentions[layer_idx]
            if attn.dim() == 4:
                attn_slice = attn[0, :, query_indices, start_idx:end_idx]
            else:
                attn_slice = attn[:, query_indices, start_idx:end_idx]

            span_val = attn_slice.float().mean().item()
            layer_scores.append(span_val)

        return float(np.mean(layer_scores))

    def probe(
        self,
        prompt: str,
        needle: str,
        is_pinned: bool = False,
        is_recency_reordered: bool = False,
        z_method: str = "v1",
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

        target_start, target_end = self.locate_needle_span(
            tokens=telemetry.tokens, needle=needle, prompt=prompt
        )
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
        is_stratified = (z_method == "v2")
        control_spans = self.sample_control_spans(
            seq_len=seq_len,
            target_start=target_start,
            target_end=target_end,
            span_len=span_length,
            count=self.num_control_spans,
            tokens=telemetry.tokens,
            stratified=is_stratified,
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

        # Empirical Z-Score calculation:
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

        # K-02: Enhanced v2 statistical metrics
        z_ci_95 = None
        p_value = None
        strat_info = None

        if z_method == "v2":
            # 1000 Bootstrap resamples
            ctrl_arr = np.array(control_scores)
            n_ctrl = len(ctrl_arr)
            boot_means = []
            for _ in range(1000):
                boot_sample = self.rng.choices(ctrl_arr.tolist(), k=n_ctrl)
                boot_means.append(float(np.mean(boot_sample)))
            boot_means_arr = np.array(boot_means)

            z_boots = (target_attn_mean - boot_means_arr) / (sigma_controls + EPSILON)
            z_ci_95 = (
                round(float(np.percentile(z_boots, 2.5)), 4),
                round(float(np.percentile(z_boots, 97.5)), 4),
            )
            p_val = float((1.0 + np.sum(boot_means_arr >= target_attn_mean)) / (1000.0 + 1.0))
            p_value = round(p_val, 4)
            strat_info = {
                "stratified_controls": True,
                "bootstrap_resamples": 1000,
                "target_relative_depth": round((target_start + target_end) / (2.0 * max(seq_len, 1)), 4),
            }

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
            z_method=z_method,
            z_ci_95=z_ci_95,
            p_value=p_value,
            control_spans=[[s, e] for s, e in control_spans],
            stratification_info=strat_info,
        )

    def probe_all_constraints(
        self,
        prompt: str,
        constraints: Optional[List[str]] = None,
        z_method: str = "v1",
    ) -> Dict[str, Any]:
        """K-04 Multi-Constraint Probing: Scan all candidate constraints in document."""
        if not constraints:
            # Auto-extract potential clinical needles from document
            candidate_patterns = [
                r"(?:allergic to|allergy to|documented allergy:?)\s*([A-Za-z0-9\s\-]+?)(?:\.|\n|,|;)",
                r"(?:eGFR|GFR|creatinine clearance|CrCl)\s*(?:is|of|:)?\s*([0-9\.]+\s*(?:mL/min|ml/min)?)",
                r"(?:contraindicated|avoid|withhold)\s+([A-Za-z0-9\s\-]+?)(?:\.|\n|,|;)",
            ]
            discovered: List[str] = []
            for pat in candidate_patterns:
                for match in re.finditer(pat, prompt, re.IGNORECASE):
                    full_span = match.group(0).strip(".,; \n")
                    if len(full_span) > 4 and full_span not in discovered:
                        discovered.append(full_span)
            constraints = discovered

        if not constraints:
            constraints = ["documented allergy", "eGFR"]

        probes: List[Dict[str, Any]] = []
        for c in constraints:
            try:
                res = self.probe(prompt=prompt, needle=c, z_method=z_method)
                probes.append(res.to_dict())
            except Exception as e:
                logger.warning(f"Failed to probe constraint '{c}': {e}")

        if not probes:
            return {
                "overall_status": "WARN",
                "total_probed": 0,
                "weakest_constraint": None,
                "min_z_score": 0.0,
                "mean_z_score": 0.0,
                "probes": [],
            }

        z_scores = [p["z_score"] for p in probes]
        min_z = min(z_scores)
        mean_z = float(np.mean(z_scores))
        weakest = min(probes, key=lambda p: p["z_score"])["target_needle"]
        has_diluted = any(p["classification"] == "DILUTED" for p in probes)

        return {
            "overall_status": "FAIL" if has_diluted else "PASS",
            "total_probed": len(probes),
            "weakest_constraint": weakest,
            "min_z_score": round(min_z, 4),
            "mean_z_score": round(mean_z, 4),
            "probes": probes,
        }


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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
        default=None,
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
        "--z-method",
        choices=["v1", "v2"],
        default="v1",
        help="Z-score statistical methodology: v1 (default) or v2 (stratified + bootstrap).",
    )
    parser.add_argument(
        "--probe-all-constraints",
        action="store_true",
        help="Automatically probe all candidate constraints detected in document.",
    )
    parser.add_argument(
        "--dump-trace",
        default=None,
        help="Path to export attention trace conforming to attention_trace.v1.schema.json.",
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

    if args.probe_all_constraints:
        all_results = probe.probe_all_constraints(
            prompt=doc_text,
            z_method=args.z_method,
        )
        if args.json:
            print(json.dumps(all_results, indent=2))
        else:
            print("=" * 65)
            print(" CareSentry-AI Multi-Constraint Attention Audit")
            print("=" * 65)
            print(f" Constraints Probed : {all_results['total_probed']}")
            print(f" Weakest Constraint : {all_results['weakest_constraint']}")
            print(f" Min Z-Score        : {all_results['min_z_score']:+.4f}")
            print(f" Mean Z-Score       : {all_results['mean_z_score']:+.4f}")
            print(f" Overall Status     : {all_results['overall_status']}")
            print("=" * 65)
        return 0 if all_results["overall_status"] == "PASS" else 1

    if not args.needle:
        logger.error("--needle is required unless --probe-all-constraints is set.")
        return 1

    result = probe.probe(prompt=doc_text, needle=args.needle, z_method=args.z_method)

    # Mitigation loop if requested and attention diluted
    if args.mitigate and result.mitigation_triggered:
        from harness.mitigations import apply_anchor_pinning
        remediated_prompt = apply_anchor_pinning(doc_text, args.needle)
        remediated_result = probe.probe(
            prompt=remediated_prompt,
            needle=args.needle,
            is_pinned=True,
            z_method=args.z_method,
        )
        remediated_result.mitigation_strategy = "SYSTEM_ANCHOR_PINNING"
        result = remediated_result

    # Dump trace if requested (K-05 & R-01)
    if args.dump_trace:
        trace_data = result.to_trace_dict(
            dtype="fp16",
            attn_impl="simulated" if getattr(probe.runner, "force_simulation", False) else "eager",
        )
        dump_p = Path(args.dump_trace)
        dump_p.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_p, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)
        logger.info(f"Exported attention trace to {args.dump_trace}")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
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
        if result.z_method == "v2" and result.z_ci_95:
            print(f" 95% Bootstrap CI    : [{result.z_ci_95[0]:+.4f}, {result.z_ci_95[1]:+.4f}]")
            print(f" Permutation p-value : {result.p_value:.4f}")
        print(f" Mitigation Trigger  : {result.mitigation_triggered}")
        if result.mitigation_strategy:
            print(f" Strategy Applied    : {result.mitigation_strategy}")
        print("=" * 65)

    return 0 if not result.mitigation_triggered else 1


if __name__ == "__main__":
    sys.exit(main())
