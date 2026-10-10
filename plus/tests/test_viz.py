"""Unit tests for F-06 Attention Heatmap Viewer."""

import json
from pathlib import Path
import pytest

from caresentry_plus.viz.heatmap_viewer import generate_heatmap_html, render_heatmap_file

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_heatmap_html_self_contained():
    """F-06 Acceptance: Self-contained HTML output with zero external CDN dependencies."""
    trace_path = FIXTURES_DIR / "baseline_neglected.trace.json"
    assert trace_path.exists()

    with open(trace_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    html = generate_heatmap_html(trace_data)
    assert "<!DOCTYPE html>" in html
    assert "CareSentry-AI Plus — Attention Heatmap Viewer" in html
    assert "RESEARCH & OBSERVABILITY TOOL ONLY" in html

    # Strict zero-CDN / no network imports check
    assert "http://" not in html
    assert "https://" not in html
    assert "cdn." not in html
    assert "unpkg.com" not in html
    assert "<script src=" not in html  # All scripts inlined


def test_side_by_side_comparative_heatmap(tmp_path):
    """F-06 Acceptance: Before and after mitigation shown side-by-side."""
    trace1 = FIXTURES_DIR / "baseline_neglected.trace.json"
    trace2 = FIXTURES_DIR / "mitigated_attended.trace.json"
    out_html = tmp_path / "comparative_heatmap.html"

    render_heatmap_file(trace1, out_html, comparative_trace_path=trace2)
    assert out_html.exists()
    content = out_html.read_text(encoding="utf-8")

    assert "split-view" in content
    assert "Baseline (Before Mitigation)" in content
    assert "Mitigated (After Intervention)" in content
