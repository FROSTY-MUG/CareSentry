"""CareSentry-AI Two-Pass Blockwise Attention-Received Estimator.

Implements K-01:
- Two-pass memory-bounded attention-received estimation.
- Pass 1 (Normalizer pass): Stream through query sequence in chunks of B_q (default 512)
  calculating per-query row log-sum-exp (LSE_i) across causal keys.
- Pass 2 (Column-gather pass): For target and control key token columns only,
  evaluate unnormalized attention logits, subtract stored LSE_i, and exponentiate:
    A(i, j) = exp(Q_i K_j^T / sqrt(d) - LSE_i) for j in {target, controls}.
- Memory footprint: O(S * K) where K is target + control tokens (typically 20-100),
  down from O(S^2) (e.g., <20 MB at 24k tokens instead of 55 GB, preventing OOM).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch

logger = logging.getLogger("caresentry.blockwise_attention")


class BlockwiseAttentionEstimator:
    """Computes exact received attention without materializing full S x S attention tensors."""

    def __init__(self, chunk_size: int = 512, epsilon: float = 1e-9):
        self.chunk_size = chunk_size
        self.epsilon = epsilon

    def compute_causal_lse(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        scale: Optional[float] = None,
    ) -> torch.Tensor:
        """Pass 1: Compute per-query row log-sum-exp (LSE) across all causal keys in chunks.

        Args:
            q: Query tensor of shape [num_heads, seq_len, head_dim]
            k: Key tensor of shape [num_heads, seq_len, head_dim]
            scale: Softmax scale factor (default 1 / sqrt(head_dim))

        Returns:
            lse: Tensor of shape [num_heads, seq_len] containing row log-sum-exp.
        """
        num_heads, seq_len, head_dim = q.shape
        if scale is None:
            scale = 1.0 / math.sqrt(head_dim)

        lse = torch.empty((num_heads, seq_len), dtype=torch.float32, device=q.device)

        # Chunk query tokens to bound memory to O(chunk_size * seq_len)
        for q_start in range(0, seq_len, self.chunk_size):
            q_end = min(seq_len, q_start + self.chunk_size)
            q_chunk = q[:, q_start:q_end, :]  # [num_heads, q_len, head_dim]

            # In causal attention, query at index i can only attend to keys j <= i
            # Maximum key needed for this chunk is q_end
            k_active = k[:, :q_end, :]  # [num_heads, q_end, head_dim]

            # logits shape: [num_heads, q_len, q_end]
            logits = torch.matmul(q_chunk, k_active.transpose(-1, -2)) * scale

            # Apply causal mask: for query i at index (q_start + row), key j > (q_start + row) is masked
            q_indices = torch.arange(q_start, q_end, device=q.device).unsqueeze(1)
            k_indices = torch.arange(0, q_end, device=q.device).unsqueeze(0)
            causal_mask = k_indices <= q_indices  # [q_len, q_end]

            # Fill masked positions with -inf
            logits = logits.masked_fill(~causal_mask.unsqueeze(0), float("-inf"))

            # LogSumExp along key dimension
            lse[:, q_start:q_end] = torch.logsumexp(logits, dim=-1)

        return lse

    def compute_span_attention_from_qk(
        self,
        q: torch.Tensor,
        k: torch.Tensor,
        start_idx: int,
        end_idx: int,
        lse: Optional[torch.Tensor] = None,
        scale: Optional[float] = None,
    ) -> float:
        """Pass 2: Gather attention directed to span [start_idx, end_idx) using stored LSE.

        Args:
            q: Query tensor of shape [num_heads, seq_len, head_dim]
            k: Key tensor of shape [num_heads, seq_len, head_dim]
            start_idx: Target/control span start key index (inclusive)
            end_idx: Target/control span end key index (exclusive)
            lse: Precomputed row log-sum-exp from Pass 1. If None, computed on the fly.
            scale: Softmax scale factor

        Returns:
            Mean attention received across all heads and subsequent query positions.
        """
        num_heads, seq_len, head_dim = q.shape
        if scale is None:
            scale = 1.0 / math.sqrt(head_dim)

        if lse is None:
            lse = self.compute_causal_lse(q, k, scale=scale)

        span_len = max(1, end_idx - start_idx)
        # In causal attention, queries strictly after or at start_idx can attend to keys
        # Specifically, subsequent query tokens that occur after the span start
        if end_idx < seq_len:
            query_start = end_idx
        else:
            query_start = max(0, start_idx)

        q_active_len = seq_len - query_start
        if q_active_len <= 0:
            query_start = max(0, seq_len - 1)
            q_active_len = 1

        # Only gather key columns for the requested span
        k_span = k[:, start_idx:end_idx, :]  # [num_heads, span_len, head_dim]

        total_attn_sum = 0.0
        total_elements = 0

        # Chunk query evaluation in Pass 2
        for q_start in range(query_start, seq_len, self.chunk_size):
            q_end = min(seq_len, q_start + self.chunk_size)
            q_chunk = q[:, q_start:q_end, :]  # [num_heads, chunk_len, head_dim]
            lse_chunk = lse[:, q_start:q_end].unsqueeze(-1)  # [num_heads, chunk_len, 1]

            # Logits to span keys only: [num_heads, chunk_len, span_len]
            span_logits = torch.matmul(q_chunk, k_span.transpose(-1, -2)) * scale

            # Mask out any key > query index (for queries that overlap the span)
            q_idx = torch.arange(q_start, q_end, device=q.device).unsqueeze(1)
            k_idx = torch.arange(start_idx, end_idx, device=q.device).unsqueeze(0)
            valid_mask = k_idx <= q_idx  # [chunk_len, span_len]

            span_logits = span_logits.masked_fill(~valid_mask.unsqueeze(0), float("-inf"))

            # Normalized attention: exp(logits - LSE)
            span_attn = torch.exp(span_logits - lse_chunk)
            span_attn = torch.nan_to_num(span_attn, nan=0.0, posinf=0.0, neginf=0.0)

            total_attn_sum += span_attn.sum().item()
            total_elements += (num_heads * (q_end - q_start) * span_len)

        return float(total_attn_sum / max(total_elements, 1))

    def evaluate_spans(
        self,
        q_by_layer: Sequence[torch.Tensor],
        k_by_layer: Sequence[torch.Tensor],
        target_span: Tuple[int, int],
        control_spans: Sequence[Tuple[int, int]],
        target_layers: Sequence[int],
    ) -> Dict[str, Any]:
        """Compute target span attention and all control span attentions across target layers."""
        t_start, t_end = target_span
        target_layer_scores: List[float] = []
        control_layer_scores: List[List[float]] = [[] for _ in control_spans]

        for layer_idx in target_layers:
            q = q_by_layer[layer_idx]
            k = k_by_layer[layer_idx]

            # Pass 1: compute LSE for this layer once
            lse = self.compute_causal_lse(q, k)

            # Pass 2: Target span
            t_score = self.compute_span_attention_from_qk(
                q=q, k=k, start_idx=t_start, end_idx=t_end, lse=lse
            )
            target_layer_scores.append(t_score)

            # Pass 2: Control spans
            for c_idx, (c_start, c_end) in enumerate(control_spans):
                c_score = self.compute_span_attention_from_qk(
                    q=q, k=k, start_idx=c_start, end_idx=c_end, lse=lse
                )
                control_layer_scores[c_idx].append(c_score)

        target_mean = float(np.mean(target_layer_scores))
        control_means = [float(np.mean(scores)) for scores in control_layer_scores]

        mu_controls = float(np.mean(control_means))
        sigma_controls = float(np.std(control_means))
        z_score = (target_mean - mu_controls) / (sigma_controls + self.epsilon)

        return {
            "target_attention_mean": round(target_mean, 6),
            "control_attention_mean": round(mu_controls, 6),
            "control_attention_std": round(sigma_controls, 6),
            "control_scores": control_means,
            "z_score": round(z_score, 4),
        }
