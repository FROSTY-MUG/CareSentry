"""Self-contained Offline Attention Heatmap Viewer (F-06).

Generates interactive, zero-network-dependency HTML visualizations of token-level
attention distributions, target needle boundaries, control spans, and Z-scores.
Supports side-by-side comparative visualization for before/after prompt mitigations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _render_single_trace_pane(trace: Dict[str, Any], pane_title: str) -> str:
    """Render a single trace container pane with tokens and styling."""
    model_id = trace.get("model_id", "Unknown Model")
    z_score = trace.get("z_score", 0.0)
    classification = trace.get("classification", "NEUTRAL").upper()
    needle_span = trace.get("needle_span", [0, 0])
    control_spans = trace.get("control_spans", [])
    per_token_att = trace.get("per_token_attention", [])
    tokens = trace.get("tokens", [])
    doc_token_count = trace.get("doc_token_count", len(tokens))
    mitigation_applied = trace.get("mitigation_applied", False)
    strategy = trace.get("mitigation_strategy") or "None"

    # Color badge for classification
    if "ATTEND" in classification:
        badge_class = "badge-success"
    elif "NEGLECT" in classification or "DILUTED" in classification:
        badge_class = "badge-danger"
    else:
        badge_class = "badge-warning"

    # Pre-calculate max attention for normalization
    max_att = max(per_token_att) if per_token_att else 1.0
    if max_att <= 0.0:
        max_att = 1e-6

    # Build token spans
    token_elements = []
    ctrl_flat = set()
    for s_idx, e_idx in control_spans:
        for k in range(s_idx, e_idx):
            ctrl_flat.add(k)

    n_start, n_end = needle_span[0], needle_span[1]

    # Handle display tokens
    display_tokens = tokens if tokens else [f"tok_{i}" for i in range(len(per_token_att))]
    
    # Cap render for initial DOM speed if enormous (>25k), with chunking
    total_toks = len(display_tokens)

    for i, tok in enumerate(display_tokens):
        att = per_token_att[i] if i < len(per_token_att) else 0.0
        # Normalized intensity [0.0 to 1.0]
        intensity = min(1.0, max(0.0, att / max_att))
        # Non-linear scaling for contrast
        scaled_intensity = math.pow(intensity, 0.6)

        is_needle = (n_start <= i < n_end)
        is_control = (i in ctrl_flat)

        classes = ["tok"]
        if is_needle:
            classes.append("needle-tok")
        elif is_control:
            classes.append("control-tok")

        # Color: interpolate from transparent to high-alpha coral/crimson
        bg_alpha = round(scaled_intensity * 0.85, 3)
        bg_style = f"background-color: rgba(220, 38, 38, {bg_alpha});" if not is_needle else "background-color: rgba(234, 179, 8, 0.45);"

        safe_tok = tok.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        token_elements.append(
            f'<span class="{" ".join(classes)}" style="{bg_style}" data-idx="{i}" data-att="{att:.6f}">{safe_tok}</span>'
        )

    tokens_html = " ".join(token_elements)

    pane_html = f"""
    <div class="trace-pane">
        <div class="pane-header">
            <h3>{pane_title}</h3>
            <div class="header-tags">
                <span class="badge {badge_class}">{classification}</span>
                <span class="badge badge-info">Z-Score: {z_score:+.3f}</span>
                <span class="badge badge-neutral">Tokens: {doc_token_count}</span>
                <span class="badge badge-strategy">Mitigation: {strategy}</span>
            </div>
        </div>
        <div class="stats-bar">
            <span><strong>Target Mean:</strong> {trace.get("target_attention_mean", 0.0):.6f}</span>
            <span><strong>Control Mean:</strong> {trace.get("control_attention_mean", 0.0):.6f}</span>
            <span><strong>Control Std:</strong> {trace.get("control_attention_std", 0.0):.6f}</span>
        </div>
        <div class="document-viewer">
            {tokens_html}
        </div>
    </div>
    """
    return pane_html


def generate_heatmap_html(
    trace: Dict[str, Any],
    comparative_trace: Optional[Dict[str, Any]] = None,
    title: str = "CareSentry-AI Attention Heatmap Viewer",
) -> str:
    """Generate self-contained interactive HTML document for one or two traces."""
    if comparative_trace is not None:
        panes_html = f"""
        <div class="panes-container split-view">
            {_render_single_trace_pane(trace, "Baseline (Before Mitigation)")}
            {_render_single_trace_pane(comparative_trace, "Mitigated (After Intervention)")}
        </div>
        """
    else:
        panes_html = f"""
        <div class="panes-container single-view">
            {_render_single_trace_pane(trace, "Attention Telemetry")}
        </div>
        """

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-red: #ef4444;
            --accent-green: #22c55e;
            --accent-amber: #f59e0b;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            padding: 20px;
            line-height: 1.5;
        }}

        header {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px 24px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo-title h1 {{
            font-size: 1.4rem;
            color: var(--accent-blue);
            font-weight: 700;
        }}

        .safety-disclaimer {{
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
            font-size: 0.8rem;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
        }}

        .panes-container {{
            display: flex;
            gap: 20px;
            width: 100%;
        }}

        .split-view .trace-pane {{
            flex: 1;
            min-width: 0;
        }}

        .single-view .trace-pane {{
            width: 100%;
        }}

        .trace-pane {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .pane-header {{
            background: #273549;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-tags {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .badge-success {{ background: #15803d; color: #dcfce7; }}
        .badge-danger {{ background: #b91c1c; color: #fee2e2; }}
        .badge-warning {{ background: #b45309; color: #fef3c7; }}
        .badge-info {{ background: #0369a1; color: #e0f2fe; }}
        .badge-strategy {{ background: #6d28d9; color: #ede9fe; }}
        .badge-neutral {{ background: #475569; color: #f1f5f9; }}

        .stats-bar {{
            background: #1e293b;
            padding: 8px 16px;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.8rem;
            color: var(--text-secondary);
            display: flex;
            gap: 16px;
        }}

        .document-viewer {{
            padding: 16px;
            max-height: 700px;
            overflow-y: auto;
            font-family: "Courier New", Courier, monospace;
            font-size: 0.95rem;
            line-height: 1.8;
            background: #0f172a;
            color: #e2e8f0;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}

        .tok {{
            display: inline-block;
            padding: 1px 3px;
            margin: 1px;
            border-radius: 2px;
            cursor: pointer;
            transition: transform 0.1s;
        }}

        .tok:hover {{
            transform: scale(1.15);
            outline: 1px solid var(--accent-blue);
            z-index: 10;
            position: relative;
        }}

        .needle-tok {{
            border: 2px solid var(--accent-amber);
            font-weight: bold;
            box-shadow: 0 0 6px rgba(245, 158, 11, 0.5);
        }}

        .control-tok {{
            border-bottom: 2px dashed #38bdf8;
        }}

        .legend {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 20px;
            margin-top: 20px;
            display: flex;
            gap: 20px;
            font-size: 0.85rem;
            align-items: center;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .legend-box {{
            width: 16px;
            height: 16px;
            border-radius: 2px;
        }}

        #token-tooltip {{
            position: fixed;
            background: #020617;
            border: 1px solid var(--accent-blue);
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            pointer-events: none;
            display: none;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo-title">
            <h1>CareSentry-AI Plus — Attention Heatmap Viewer</h1>
            <p style="font-size: 0.8rem; color: var(--text-secondary);">Interactive Empirical Attention Sentry & Invariant Observability</p>
        </div>
        <div class="safety-disclaimer">
            RESEARCH & OBSERVABILITY TOOL ONLY — NOT FOR CLINICAL DECISION-MAKING
        </div>
    </header>

    {panes_html}

    <div class="legend">
        <strong>Legend:</strong>
        <div class="legend-item">
            <span class="legend-box" style="border: 2px solid var(--accent-amber); background: rgba(245, 158, 11, 0.4);"></span>
            <span>Target Constraint (Needle)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="border-bottom: 2px dashed #38bdf8; background: rgba(56, 189, 248, 0.2);"></span>
            <span>Control Spans (Background Context)</span>
        </div>
        <div class="legend-item">
            <span class="legend-box" style="background: rgba(220, 38, 38, 0.8);"></span>
            <span>High Relative Attention Density</span>
        </div>
    </div>

    <div id="token-tooltip"></div>

    <script>
        const tooltip = document.getElementById('token-tooltip');
        document.querySelectorAll('.tok').forEach(el => {{
            el.addEventListener('mouseenter', (e) => {{
                const idx = el.getAttribute('data-idx');
                const att = el.getAttribute('data-att');
                tooltip.innerHTML = `<strong>Token Index:</strong> ${{idx}}<br><strong>Attention Mass:</strong> ${{att}}`;
                tooltip.style.display = 'block';
            }});
            el.addEventListener('mousemove', (e) => {{
                tooltip.style.left = (e.clientX + 12) + 'px';
                tooltip.style.top = (e.clientY + 12) + 'px';
            }});
            el.addEventListener('mouseleave', () => {{
                tooltip.style.display = 'none';
            }});
        }});
    </script>
</body>
</html>
"""
    return html_template


def render_heatmap_file(
    trace_path: Path,
    output_path: Path,
    comparative_trace_path: Optional[Path] = None,
) -> Path:
    """Render heatmap HTML file directly from trace JSON paths."""
    with open(trace_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    comp_data = None
    if comparative_trace_path and comparative_trace_path.exists():
        with open(comparative_trace_path, "r", encoding="utf-8") as f:
            comp_data = json.load(f)

    html_content = generate_heatmap_html(trace_data, comp_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
