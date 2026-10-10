"""Evaluate Evidence Grounding Engine on Labeled Dataset."""

import json
import sys
from pathlib import Path

# Bootstrap sys.path for guard/src
GUARD_SRC = Path(__file__).resolve().parent.parent / "src"
if str(GUARD_SRC) not in sys.path:
    sys.path.insert(0, str(GUARD_SRC))

from caresentry_guard.grounding.engine import EvidenceGroundingEngine


def run_grounding_evaluation() -> dict:
    data_path = Path(__file__).resolve().parent.parent / "data_guard" / "grounding_eval.json"
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    ehr_text = dataset["ehr"]
    sentences = dataset["sentences"]
    engine = EvidenceGroundingEngine()

    tp = 0  # correctly flagged as unsupported
    fp = 0  # supported incorrectly flagged as unsupported
    tn = 0  # supported correctly passed
    fn = 0  # unsupported missed (treated as supported)

    safety_critical_unsupported_caught = 0
    total_safety_critical_unsupported = 0

    for item in sentences:
        s_text = item["text"]
        true_label = item["label"]  # "supported" or "unsupported"
        is_crit = item.get("critical", False)

        report = engine.audit_grounding(ehr_text, s_text)
        attr = report.sentence_attributions[0]
        pred_unsupported = attr.status in ["unsupported", "weak"]

        if true_label == "unsupported":
            if is_crit:
                total_safety_critical_unsupported += 1
            if pred_unsupported:
                tp += 1
                if is_crit:
                    safety_critical_unsupported_caught += 1
            else:
                fn += 1
        else:
            if pred_unsupported:
                fp += 1
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    crit_recall = (
        safety_critical_unsupported_caught / total_safety_critical_unsupported
        if total_safety_critical_unsupported > 0
        else 0.0
    )

    metrics = {
        "benchmark": "CareSentry Guard Evidence Grounding Evaluation",
        "total_sentences": len(sentences),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "hallucination_detection_precision": round(precision, 4),
        "hallucination_detection_recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "safety_critical_recall": round(crit_recall, 4),
    }

    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "grounding_eval_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    results = run_grounding_evaluation()
    print("=" * 60)
    print(" CareSentry Guard Evidence Grounding Evaluation Results")
    print("=" * 60)
    for k, v in results.items():
        print(f" {k:<36}: {v}")
    print("=" * 60)
