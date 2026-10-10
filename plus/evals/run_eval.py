"""Large-scale deterministic benchmark runner (F-05).

Executes rule validation, reverse omission audits, and attention probe evaluations
across >= 100 synthetic cases. Computes statistical metrics with 95% confidence intervals.
Outputs verified JSON results only to plus/evals/results/.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from caresentry_plus.adapters.probe_shim import ProbeShim
from caresentry_plus.extraction.omission_checker import OmissionChecker
from caresentry_plus.rules.engine import RulePackEngine

DATA_PATH = Path(__file__).resolve().parent.parent / "data_plus" / "synthetic_cases.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_FILE = RESULTS_DIR / "benchmark_summary.json"


def compute_wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Compute Wilson score 95% confidence interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    z = 1.95996  # 95% confidence
    p = k / n
    denominator = 1.0 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return round(lower, 4), round(upper, 4)


def run_evaluation() -> Dict[str, Any]:
    """Execute complete offline evaluation suite across synthetic cohort."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Synthetic test data not found at {DATA_PATH}. Run generate_cases.py first.")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    engine = RulePackEngine()
    omission_checker = OmissionChecker()
    probe_shim = ProbeShim(fallback_mode=True)

    # Invariant violation metrics
    v_tp = 0
    v_fp = 0
    v_fn = 0
    v_tn = 0

    # Omission metrics
    o_tp = 0
    o_fn = 0
    o_tn = 0
    o_fp = 0

    # Mitigation rescue metrics
    neglected_count = 0
    rescued_count = 0

    total_cases = len(cases)
    per_depth_stats = {
        "early": {"total": 0, "violations_detected": 0},
        "middle": {"total": 0, "violations_detected": 0},
        "late": {"total": 0, "violations_detected": 0},
    }

    for case in cases:
        record = case["patient_record"]
        summary = case["discharge_summary"]
        is_violation = case["is_violation"]
        is_omission = case["is_omission"]
        depth = case["target_depth_fraction"]

        depth_key = "early" if depth < 0.3 else ("late" if depth > 0.7 else "middle")
        per_depth_stats[depth_key]["total"] += 1

        # 1. Evaluate Invariant Violations
        violations = engine.evaluate_invariants(record, summary)
        has_violations = len(violations) > 0

        if is_violation:
            if has_violations:
                v_tp += 1
                per_depth_stats[depth_key]["violations_detected"] += 1
            else:
                v_fn += 1
        else:
            if has_violations:
                v_fp += 1
            else:
                v_tn += 1

        # 2. Evaluate Reverse Omissions
        omissions = omission_checker.check_omissions(record, summary)
        has_omissions = len(omissions) > 0

        if is_omission:
            if has_omissions:
                o_tp += 1
            else:
                o_fn += 1
        else:
            if has_omissions:
                o_fp += 1
            else:
                o_tn += 1

        # 3. Evaluate Attention Probe & Mitigation Rescue
        needle = case["needle_text"]
        baseline_trace = probe_shim.probe(record, needle, apply_mitigation=False)
        if baseline_trace.z_score < -0.5:
            neglected_count += 1
            mitigated_trace = probe_shim.probe(record, needle, apply_mitigation=True)
            if mitigated_trace.z_score >= 0.5:
                rescued_count += 1

    # Statistical Computations
    violation_recall = v_tp / (v_tp + v_fn) if (v_tp + v_fn) > 0 else 0.0
    violation_prec = v_tp / (v_tp + v_fp) if (v_tp + v_fp) > 0 else 0.0
    violation_fpr = v_fp / (v_fp + v_tn) if (v_fp + v_tn) > 0 else 0.0
    v_recall_ci = compute_wilson_ci(v_tp, v_tp + v_fn)

    omission_recall = o_tp / (o_tp + o_fn) if (o_tp + o_fn) > 0 else 0.0
    o_recall_ci = compute_wilson_ci(o_tp, o_tp + o_fn)

    rescue_rate = rescued_count / neglected_count if neglected_count > 0 else 1.0
    rescue_ci = compute_wilson_ci(rescued_count, neglected_count)

    results_payload = {
        "benchmark_metadata": {
            "total_cases_evaluated": total_cases,
            "engine_rule_packs": engine.loaded_pack_ids,
            "ontology_version": engine.normalizer.ontology_version,
            "seed": 42,
        },
        "metrics": {
            "violation_recall": round(violation_recall, 4),
            "violation_recall_95ci": list(v_recall_ci),
            "violation_precision": round(violation_prec, 4),
            "false_positive_rate": round(violation_fpr, 4),
            "omission_recall": round(omission_recall, 4),
            "omission_recall_95ci": list(o_recall_ci),
            "mitigation_rescue_rate": round(rescue_rate, 4),
            "mitigation_rescue_95ci": list(rescue_ci),
        },
        "counts": {
            "violation_true_positives": v_tp,
            "violation_false_positives": v_fp,
            "violation_false_negatives": v_fn,
            "violation_true_negatives": v_tn,
            "omission_true_positives": o_tp,
            "omission_false_negatives": o_fn,
            "neglected_needles_count": neglected_count,
            "rescued_needles_count": rescued_count,
        },
        "needle_depth_breakdown": per_depth_stats,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    return results_payload


def print_results_table(results: Dict[str, Any]) -> None:
    """Print clean summary table without external rich dependencies if needed."""
    m = results["metrics"]
    c = results["counts"]
    meta = results["benchmark_metadata"]

    print("\n" + "=" * 70)
    print("      CARESENTRY-AI PLUS LARGE-SCALE EVALUATION BENCHMARK")
    print("=" * 70)
    print(f"Total Cohort Cases Evaluated: {meta['total_cases_evaluated']}")
    print(f"Rule Packs Active:            {', '.join(meta['engine_rule_packs'])}")
    print("-" * 70)
    print(f"Violation Recall:             {m['violation_recall']:.2%}  (95% CI: [{m['violation_recall_95ci'][0]:.2%}, {m['violation_recall_95ci'][1]:.2%}])")
    print(f"Violation Precision:          {m['violation_precision']:.2%}")
    print(f"False Positive Rate:          {m['false_positive_rate']:.2%}")
    print(f"Omission Recall (Reverse):    {m['omission_recall']:.2%}  (95% CI: [{m['omission_recall_95ci'][0]:.2%}, {m['omission_recall_95ci'][1]:.2%}])")
    print(f"Mitigation Rescue Rate:       {m['mitigation_rescue_rate']:.2%}  (95% CI: [{m['mitigation_rescue_95ci'][0]:.2%}, {m['mitigation_rescue_95ci'][1]:.2%}])")
    print("=" * 70)
    print(f"Results written to {RESULTS_FILE}\n")


if __name__ == "__main__":
    res = run_evaluation()
    print_results_table(res)
