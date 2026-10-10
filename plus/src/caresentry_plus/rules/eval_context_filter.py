"""Evaluator for ContextFilter against labeled ground truth dataset.

Calculates multi-class precision, recall, and safety fail-safe preservation.
"""

from __future__ import annotations

from typing import Any, Dict

from caresentry_plus.rules.context_filter import ContextFilter
from caresentry_plus.rules.labeled_dataset import LABELED_ASSERTION_DATASET


def evaluate_context_filter() -> Dict[str, Any]:
    """Run comprehensive assertion classification benchmark."""
    filter_engine = ContextFilter()

    total = len(LABELED_ASSERTION_DATASET)
    status_matches = 0
    active_matches = 0

    # Per status tracking
    classes = ["AFFIRMED", "NEGATED", "HISTORICAL", "FAMILY_HISTORY", "AMBIGUOUS"]
    tp = {c: 0 for c in classes}
    fp = {c: 0 for c in classes}
    fn = {c: 0 for c in classes}

    safety_violations = 0  # Where ground truth was active risk, but filter marked it suppressed

    for item in LABELED_ASSERTION_DATASET:
        text = item["text"]
        entity = item["entity"]
        exp_status = item["expected_status"]
        exp_active = item["expected_active"]

        assertion = filter_engine.analyze_assertion(text, entity)
        pred_status = assertion.status.value
        pred_active = assertion.is_active_risk

        if pred_status == exp_status:
            status_matches += 1
            tp[exp_status] += 1
        else:
            fp[pred_status] += 1
            fn[exp_status] += 1

        if pred_active == exp_active:
            active_matches += 1

        # Check safety invariant: Never suppress an active risk!
        if exp_active and not pred_active:
            safety_violations += 1

    per_class_metrics = {}
    for c in classes:
        prec = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        rec = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class_metrics[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp[c] + fn[c],
        }

    overall_accuracy = status_matches / total
    active_accuracy = active_matches / total

    # Macro averages
    macro_prec = sum(m["precision"] for m in per_class_metrics.values()) / len(classes)
    macro_rec = sum(m["recall"] for m in per_class_metrics.values()) / len(classes)
    macro_f1 = sum(m["f1"] for m in per_class_metrics.values()) / len(classes)

    return {
        "total_samples": total,
        "status_accuracy": round(overall_accuracy, 4),
        "active_risk_accuracy": round(active_accuracy, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "safety_violations_count": safety_violations,
        "fail_safe_guarantee": safety_violations == 0,
        "per_class": per_class_metrics,
    }


if __name__ == "__main__":
    import json
    res = evaluate_context_filter()
    print(json.dumps(res, indent=2))
