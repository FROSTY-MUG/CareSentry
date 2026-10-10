"""Tests for K-01 Two-Pass Blockwise Attention Estimator."""

import math
import torch
import pytest
from harness.blockwise_attention import BlockwiseAttentionEstimator


def test_blockwise_attention_matches_standard_softmax():
    """Verify that BlockwiseAttentionEstimator matches standard causal softmax attention."""
    torch.manual_seed(42)
    num_heads = 2
    seq_len = 64
    head_dim = 16
    chunk_size = 16  # Force multi-chunk execution

    q = torch.randn(num_heads, seq_len, head_dim)
    k = torch.randn(num_heads, seq_len, head_dim)

    estimator = BlockwiseAttentionEstimator(chunk_size=chunk_size)

    # 1. Standard full causal softmax attention
    scale = 1.0 / math.sqrt(head_dim)
    full_logits = torch.matmul(q, k.transpose(-1, -2)) * scale
    causal_mask = torch.tril(torch.ones(seq_len, seq_len, dtype=torch.bool))
    full_logits = full_logits.masked_fill(~causal_mask.unsqueeze(0), float("-inf"))
    full_attn = torch.softmax(full_logits, dim=-1)

    # 2. Blockwise LSE from Pass 1
    lse = estimator.compute_causal_lse(q, k, scale=scale)
    # Expected LSE
    expected_lse = torch.logsumexp(full_logits, dim=-1)
    assert torch.allclose(lse, expected_lse, atol=1e-5)

    # 3. Test span attention for target span [10, 15)
    t_start, t_end = 10, 15
    blockwise_score = estimator.compute_span_attention_from_qk(
        q=q, k=k, start_idx=t_start, end_idx=t_end, lse=lse, scale=scale
    )

    # Ground truth calculation from full_attn:
    # Query positions strictly after t_end: range(15, 64)
    query_indices = list(range(t_end, seq_len))
    expected_slice = full_attn[:, query_indices, t_start:t_end]
    expected_score = float(expected_slice.mean().item())

    assert pytest.approx(blockwise_score, abs=1e-5) == expected_score


def test_blockwise_attention_multi_layer_eval():
    """Verify multi-layer span evaluation and z-score calculation."""
    torch.manual_seed(123)
    num_heads = 4
    seq_len = 128
    head_dim = 32

    q_layers = [torch.randn(num_heads, seq_len, head_dim) for _ in range(4)]
    k_layers = [torch.randn(num_heads, seq_len, head_dim) for _ in range(4)]

    estimator = BlockwiseAttentionEstimator(chunk_size=32)

    target_span = (20, 25)
    control_spans = [(5, 10), (30, 35), (40, 45), (50, 55), (60, 65)]

    results = estimator.evaluate_spans(
        q_by_layer=q_layers,
        k_by_layer=k_layers,
        target_span=target_span,
        control_spans=control_spans,
        target_layers=[2, 3],
    )

    assert "target_attention_mean" in results
    assert "control_attention_mean" in results
    assert "z_score" in results
    assert len(results["control_scores"]) == 5
    assert not math.isnan(results["z_score"])
