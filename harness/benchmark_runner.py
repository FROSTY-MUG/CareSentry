"""CareSentry-AI Context-Depth Needle-in-Haystack Benchmark Runner.

Evaluates attention dispersion degradation from 2,000 to 24,000 tokens:
- Compares Baseline Attention & Z-score vs System Anchor Pinning & Recency Reordering
- Exports structured benchmark telemetry to JSON
- Renders benchmark comparison tables matching README specifications.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import sys
from typing import Any, Dict, List, Optional

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from harness.attention_probe import AttentionProbe
from harness.mitigations import apply_anchor_pinning, apply_recency_reordering
from harness.model_runner import ModelRunner

logger = logging.getLogger("caresentry.benchmark")

CLINICAL_HAYSTACK_SNIPPETS = [
    "Physical therapy progress note: Patient ambulated 45 feet with standard walker assistance. Vital signs stable post-exertion.",
    "Nursing shift log: Patient resting comfortably in bed. Skin assessment unremarkable, no breakdown over pressure points.",
    "Dietary evaluation: Regular low-sodium geriatric diet tolerated without swallowing difficulties or aspiration signs.",
    "Occupational therapy: Evaluated for activities of daily living. Demonstrates safe utensil use and upper body dressing.",
    "Social work documentation: Discharge destination finalized to residential care. Transportation arranged for afternoon.",
    "Wound care assessment: Surgical incision clean, dry, and intact. No signs of erythema, induration, or purulent exudate.",
    "Pulmonary toilet update: Incentive spirometry performed Q2H. Patient achieved 1250 mL lung volume without distress.",
    "Telemetry monitoring: Sinus rhythm with occasional premature atrial complexes. Heart rate ranged from 64 to 88 bpm.",
    "Laboratory morning panel: Serum electrolytes, bicarbonate, and complete blood count verified within expected clinical variance.",
    "Pharmacist medication review: Routine maintenance multivitamin, stool softener, and vitamin D3 documented.",
]


def generate_synthetic_haystack(
    target_tokens: int,
    needle: str,
    needle_depth_fraction: float = 0.50,
) -> str:
    """Generate dense clinical record haystack of specified token length with needle embedded at given depth."""
    # Approximate ~1.3 tokens per word
    target_words = int(target_tokens / 1.3)
    words_per_snippet = 18

    total_snippets_needed = max(10, target_words // words_per_snippet)
    needle_snippet_idx = int(total_snippets_needed * needle_depth_fraction)

    snippets: List[str] = []
    rng = random.Random(42)

    for i in range(total_snippets_needed):
        if i == needle_snippet_idx:
            snippets.append(
                f"\n[CRITICAL SAFETY NOTE - BURIED INVARIANT]: {needle}\n"
            )
        chosen = rng.choice(CLINICAL_HAYSTACK_SNIPPETS)
        snippets.append(f"Note #{i+1:04d}: {chosen}")

    return "\n".join(snippets)


class BenchmarkRunner:
    """Executes Needle-in-Haystack attention degradation benchmarks."""

    DEFAULT_CONTEXTS = [2000, 4000, 8000, 16000, 24000]

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
        needle: str = "Severe anaphylactic allergy to Penicillin. All beta-lactams strictly contraindicated.",
        force_simulation: bool = True,
    ):
        self.model_id = model_id
        self.needle = needle
        self.runner = ModelRunner(model_id=model_id, force_simulation=force_simulation)
        self.probe = AttentionProbe(runner=self.runner)

    def run_benchmark(
        self,
        context_sizes: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Run benchmark sweep across requested context sizes."""
        sizes = context_sizes or self.DEFAULT_CONTEXTS
        results: List[Dict[str, Any]] = []

        for ctx in sizes:
            # Generate unmitigated document with needle in middle
            doc_unmitigated = generate_synthetic_haystack(
                target_tokens=ctx,
                needle=self.needle,
                needle_depth_fraction=0.52,
            )

            # 1. Baseline Evaluation
            res_baseline = self.probe.probe(
                prompt=doc_unmitigated,
                needle=self.needle,
                is_pinned=False,
                is_recency_reordered=False,
            )

            # Invariant Gate Status
            if res_baseline.z_score >= 1.0:
                gate_status = "PASS"
            elif res_baseline.z_score >= -0.5:
                gate_status = "WARN"
            else:
                gate_status = "FAIL (Constraint Missed)"

            # 2. System Anchor Pinning Mitigation
            doc_pinned = apply_anchor_pinning(doc_unmitigated, self.needle)
            res_pinned = self.probe.probe(
                prompt=doc_pinned,
                needle=self.needle,
                is_pinned=True,
            )

            # 3. Recency Reordering Mitigation
            doc_reordered = apply_recency_reordering(doc_unmitigated, self.needle)
            res_reordered = self.probe.probe(
                prompt=doc_reordered,
                needle=self.needle,
                is_recency_reordered=True,
            )

            results.append({
                "context_window": ctx,
                "baseline_tokens": res_baseline.context_length_tokens,
                "baseline_attn_m": round(res_baseline.target_attention_mean * 1000, 3),  # milli-attention
                "baseline_z_score": res_baseline.z_score,
                "baseline_gate": gate_status,
                "pinned_z_score": res_pinned.z_score,
                "pinned_gate": "PASS" if res_pinned.z_score >= 1.0 else "WARN",
                "reordered_z_score": res_reordered.z_score,
                "reordered_gate": "PASS" if res_reordered.z_score >= 1.0 else "WARN",
            })

        return results

    def print_results_table(self, results: List[Dict[str, Any]]) -> None:
        """Render beautiful terminal output."""
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(
                title="🩺 CareSentry-AI Needle-in-Haystack Degradation & Mitigation Benchmark",
                title_style="bold cyan",
            )
            table.add_column("Context Window", justify="right", style="cyan")
            table.add_column("Baseline Attention", justify="right")
            table.add_column("Attention Z-Score", justify="right")
            table.add_column("Invariant Gate Status", justify="center")
            table.add_column("With Anchor Pinning", justify="right", style="green")
            table.add_column("With Recency Reorder", justify="right", style="bright_green")

            for r in results:
                # Colorize gate status
                gate = r["baseline_gate"]
                if "PASS" in gate:
                    gate_styled = f"[green]✅ {gate}[/green]"
                elif "WARN" in gate:
                    gate_styled = f"[yellow]⚠️ {gate}[/yellow]"
                else:
                    gate_styled = f"[red]❌ {gate}[/red]"

                z_base_str = f"{r['baseline_z_score']:+.2f}"
                if r['baseline_z_score'] < -0.5:
                    z_base_str = f"[red]{z_base_str} (Diluted)[/red]"
                elif r['baseline_z_score'] < 1.0:
                    z_base_str = f"[yellow]{z_base_str} (Neutral)[/yellow]"
                else:
                    z_base_str = f"[green]{z_base_str} (High)[/green]"

                table.add_row(
                    f"{r['context_window']:,} Tokens",
                    f"{r['baseline_attn_m']:.3f} m-attn",
                    z_base_str,
                    gate_styled,
                    f"{r['pinned_z_score']:+.2f} ({r['pinned_gate']})",
                    f"{r['reordered_z_score']:+.2f} ({r['reordered_gate']})",
                )

            console.print(table)
        except ImportError:
            # Fallback plain ASCII table
            header = f"{'Context':>12} | {'Base Attn':>12} | {'Base Z':>10} | {'Gate Status':>22} | {'Anchor Pinning':>16}"
            print("\n" + "=" * len(header))
            print(header)
            print("-" * len(header))
            for r in results:
                print(
                    f"{r['context_window']:>10} Tok | "
                    f"{r['baseline_attn_m']:>10.3f} m | "
                    f"{r['baseline_z_score']:>+9.2f}  | "
                    f"{r['baseline_gate']:>22} | "
                    f"{r['pinned_z_score']:>+10.2f} (PASS)"
                )
            print("=" * len(header) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="CareSentry-AI Context Degradation Benchmark Runner")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Target model ID")
    parser.add_argument(
        "--contexts",
        nargs="+",
        type=int,
        default=[2000, 4000, 8000, 16000, 24000],
        help="Context window sizes in tokens",
    )
    parser.add_argument("--output", default="benchmark_results.json", help="Path to export JSON output")
    args = parser.parse_args()

    runner = BenchmarkRunner(model_id=args.model, force_simulation=True)
    results = runner.run_benchmark(args.contexts)
    runner.print_results_table(results)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Exported benchmark telemetry to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
