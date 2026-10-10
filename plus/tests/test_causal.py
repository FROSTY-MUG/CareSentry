"""Unit tests for F-07 and F-08 Causal Validation and Per-Head Analysis."""

import pytest
from caresentry_plus.causal.ablation import CausalAblationTester
from caresentry_plus.causal.per_head import PerHeadAnalyzer


def test_causal_ablation_counterfactual():
    """F-07: Test 3-arm counterfactual needle ablation."""
    tester = CausalAblationTester()
    prompt = "Patient has severe penicillin allergy. Discharged on stable condition."
    needle = "Patient has severe penicillin allergy."

    results = tester.run_ablation_experiment(prompt, needle)
    assert "baseline" in results
    assert "needle_ablated" in results
    assert "control_ablated" in results
    assert "causal_metrics" in results
    assert results["causal_metrics"]["causal_effect_size"] > 0


def test_per_head_analysis_retrieval_ranking():
    """F-08: Discover retrieval heads and compare layer grouping."""
    analyzer = PerHeadAnalyzer(num_layers=28, num_heads=16)
    analysis = analyzer.analyze_attention_distribution()

    assert "top_retrieval_heads" in analysis
    assert len(analysis["top_retrieval_heads"]) == 10
    assert "layer_comparison" in analysis
    assert "track_a_last_4_layers" in analysis["layer_comparison"]
    assert "recommendation" in analysis
