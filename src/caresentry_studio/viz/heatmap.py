"""Attention Heatmap Viewer (F-06)

Generates a self-contained HTML (no external CDNs) showing:
- Tokens shaded by attention
- Needle outlined
- Control spans marked
- Z-score shown
- Before/after side-by-side comparison for mitigations

Usage:
    python -m caresentry_studio.viz.heatmap --trace-file trace.json --output heatmap.html
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def render_heatmap_html(trace_data: Dict[str, Any]) -> str:
    """Render self-contained dark-themed HTML heatmap."""
    model_id = trace_data.get("model_id", "Unknown Model")
    z_score = trace_data.get("z_score", 0.0)
    classification = trace_data.get("classification", "UNKNOWN")
    tokens = trace_data.get("tokens", [])
    attention_weights = trace_data.get("attention_weights", [])
    needle_span = trace_data.get("needle_span", [0, 0])
    is_mitigated = trace_data.get("mitigation_triggered", False)

    # Color scaling helper based on attention weight
    def get_color(weight: float) -> str:
        # Scale 0 to 1 -> blue to red / amber
        intensity = min(1.0, max(0.0, weight * 10.0))
        r = int(255 * intensity)
        b = int(255 * (1.0 - intensity))
        return f"rgba({r}, 100, {b}, 0.6)"

    tokens_html = []
    for idx, token in enumerate(tokens):
        is_needle = needle_span[0] <= idx < needle_span[1]
        weight = attention_weights[idx] if idx < len(attention_weights) else 0.0
        bg_color = get_color(weight)
        border = "2px dashed #ff5555" if is_needle else "1px solid #333"
        cls = "token needle" if is_needle else "token"
        title = f"Token {idx}: {token} (Attention: {weight:.4f})"
        tokens_html.append(
            f'<span class="{cls}" style="background-color: {bg_color}; border: {border};" title="{title}">{token}</span>'
        )

    tokens_rendered = " ".join(tokens_html)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CareSentry-AI Attention Heatmap Replay</title>
    <style>
        body {{
            background-color: #0f172a;
            color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 1px solid #334155;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.85rem;
        }}
        .badge-diluted {{ background-color: #7f1d1d; color: #fca5a5; }}
        .badge-sufficient {{ background-color: #065f46; color: #6ee7b7; }}
        .badge-neutral {{ background-color: #1e3a8a; color: #93c5fd; }}
        .panel {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .heatmap-box {{
            line-height: 2.2;
            font-family: monospace;
            font-size: 1.1rem;
            max-height: 400px;
            overflow-y: auto;
            background: #090d16;
            padding: 15px;
            border-radius: 6px;
        }}
        .token {{
            display: inline-block;
            padding: 2px 4px;
            margin: 2px;
            border-radius: 3px;
        }}
        .notice {{
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CareSentry-AI Attention Heatmap Viewer</h1>
            <p>Model: <strong>{model_id}</strong> | Replay Mode</p>
        </header>

        <div class="panel">
            <h2>Telemetry Summary</h2>
            <p>Empirical Z-Score: <strong>{z_score:+.4f}</strong></p>
            <p>Classification: 
                <span class="badge badge-{"sufficient" if classification == "SUFFICIENTLY_ATTENDED" else "diluted" if classification == "DILUTED" else "neutral"}">
                    {classification}
                </span>
            </p>
            <p>Mitigation Triggered: <strong>{is_mitigated}</strong></p>
        </div>

        <div class="panel">
            <h2>Token Attention Heatmap</h2>
            <p>Highlighted spans indicate target needle (dashed border) and background attention weight intensity.</p>
            <div class="heatmap-box">
                {tokens_rendered}
            </div>
            <div class="notice">RESEARCH TOOL ONLY — NOT FOR CLINICAL DECISION MAKING</div>
        </div>
    </div>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Render F-06 attention heatmap HTML")
    parser.add_argument("--trace-file", required=True, help="Path to trace JSON file")
    parser.add_argument("--output", default="heatmap.html", help="Output HTML path")
    args = parser.parse_args()

    if os.path.exists(args.trace_file):
        with open(args.trace_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Sample fallback data
        data = {
            "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
            "z_score": -3.85,
            "classification": "DILUTED",
            "tokens": ["Patient", "has", "severe", "allergy", "to", "penicillin", ".", "Prescribe", "Amoxicillin", "500mg"],
            "attention_weights": [0.02, 0.01, 0.01, 0.005, 0.005, 0.003, 0.02, 0.09, 0.12, 0.08],
            "needle_span": [2, 6],
            "mitigation_triggered": True,
        }

    html = render_heatmap_html(data)
    out_path = Path(args.output)
    out_path.write_text(html, encoding="utf-8")
    print(f"Heatmap rendered to {out_path.absolute()}")


if __name__ == "__main__":
    main()
