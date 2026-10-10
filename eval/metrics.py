"""metrics.py

Statistical metrics for CareSentry evaluation.
Computes:
- Violation recall: fraction of cases with violations correctly detected
- False positive rate: fraction of clean cases incorrectly flagged
- Omission recall: fraction of missing critical constraints detected (when CLINICAL present)
- Rescue rate: fraction of mitigated cases where attention was rescued (when traces exist)
- Confidence intervals using Wilson score method
"""

import math
from typing import List, Tuple

def wilson_score_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    phat = k / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def violation_recall(detected: int, total: int) -> float:
    """Fraction of violations correctly detected."""
    if total == 0:
        return 0.0
    return detected / total


def false_positive_rate(fp: int, total_clean: int) -> float:
    """Fraction of clean cases incorrectly flagged."""
    if total_clean == 0:
        return 0.0
    return fp / total_clean


def omission_recall(detected: int, total_omissions: int) -> float:
    """Fraction of missing constraints detected."""
    if total_omissions == 0:
        return 0.0
    return detected / total_omissions


def rescue_rate(rescued: int, total_mitigations: int) -> float:
    """Fraction of mitigated cases where attention was rescued."""
    if total_mitigations == 0:
        return 0.0
    return rescued / total_mitigations


def compute_metrics(results: List[dict]) -> dict:
    """Compute all metrics from evaluation results."""
    total = len(results)
    violations = [r for r in results if r.get("has_violation", False)]
    clean = [r for r in results if not r.get("has_violation", False)]
    detected_violations = [r for r in violations if r.get("violation_detected", False)]
    false_positives = [r for r in clean if r.get("violation_detected", False)]

    total_violations = len(violations)
    total_clean = len(clean)
    detected_count = len(detected_violations)
    fp_count = len(false_positives)

    vr = violation_recall(detected_count, total_violations)
    fpr = false_positive_rate(fp_count, total_clean)

    vr_ci = wilson_score_interval(detected_count, total_violations)
    fpr_ci = wilson_score_interval(fp_count, total_clean)

    # Omission recall (when CLINICAL present)
    omissions = [r for r in results if r.get("has_omission", False)]
    detected_omissions = [r for r in omissions if r.get("omission_detected", False)]
    omission_recall_val = omission_recall(len(detected_omissions), len(omissions))

    # Rescue rate (when traces exist)
    mitigations = [r for r in results if r.get("mitigation_triggered", False)]
    rescued = [r for r in mitigations if r.get("rescued", False)]
    rescue_rate_val = rescue_rate(len(rescued), len(mitigations))

    return {
        "total_cases": total,
        "total_violations": total_violations,
        "total_clean": total_clean,
        "violation_recall": round(vr, 4),
        "violation_recall_ci": [round(vr_ci[0], 4), round(vr_ci[1], 4)],
        "false_positive_rate": round(fpr, 4),
        "false_positive_rate_ci": [round(fpr_ci[0], 4), round(fpr_ci[1], 4)],
        "omission_recall": round(omission_recall_val, 4),
        "rescue_rate": round(rescue_rate_val, 4),
    }