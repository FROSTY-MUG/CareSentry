"""Tests for src/caresentry_studio/viz/heatmap.py"""

import json
import sys
from pathlib import Path
import pytest

# Ensure caresentry_studio is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from caresentry_studio.viz.heatmap import render_heatmap_html

def test_heatmap_renders(tmp_path):
    # Sample trace data
    trace_data = {
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "z_score": -3.85,
        "classification": "DILUTED",
        "tokens": ["Patient", "has", "severe", "allergy", "to", "penicillin", ".", "Prescribe", "Amoxicillin", "500mg"],
        "attention_weights": [0.02, 0.01, 0.01, 0.005, 0.005, 0.003, 0.02, 0.09, 0.12, 0.08],
        "needle_span": [2, 6],
        "mitigation_triggered": True,
    }
    html = render_heatmap_html(trace_data)
    assert isinstance(html, str)
    assert len(html) > 1000
    assert "heatmap-box" in html
    assert "needle" in html
    assert "DILUTED" in html


def test_heatmap_fallback():
    html = render_heatmap_html({"model_id": "Test"})
    assert isinstance(html, str)
    assert "Test" in html
