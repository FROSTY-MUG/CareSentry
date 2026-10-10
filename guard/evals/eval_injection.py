"""Evaluate Clinical Injection Scanner on Labeled Dataset."""

import json
import sys
from pathlib import Path

# Bootstrap sys.path for guard/src
GUARD_SRC = Path(__file__).resolve().parent.parent / "src"
if str(GUARD_SRC) not in sys.path:
    sys.path.insert(0, str(GUARD_SRC))

from caresentry_guard.injection.scanner import ClinicalInjectionScanner, InjectionAction


def run_injection_evaluation() -> dict:
    data_path = Path(__file__).resolve().parent.parent / "data_guard" / "injection_eval.json"
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    scanner = ClinicalInjectionScanner(action=InjectionAction.FLAG)

    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0

    # Evaluate Benign (Target: label=0, has_injection=False)
    for item in dataset["benign"]:
        res = scanner.scan(item["text"])
        if res.has_injection:
            false_positives += 1
        else:
            true_negatives += 1

    # Evaluate Malicious (Target: label=1, has_injection=True)
    for item in dataset["malicious"]:
        res = scanner.scan(item["text"])
        if res.has_injection:
            true_positives += 1
        else:
            false_negatives += 1

    total_benign = len(dataset["benign"])
    total_malicious = len(dataset["malicious"])

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / total_malicious if total_malicious > 0 else 0.0
    fpr = false_positives / total_benign if total_benign > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics = {
        "benchmark": "CareSentry Guard Prompt-Injection Evaluation",
        "total_samples": total_benign + total_malicious,
        "benign_samples": total_benign,
        "malicious_samples": total_malicious,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(fpr, 4),
        "f1_score": round(f1, 4),
    }

    # Save results to evals/results/
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "injection_eval_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    results = run_injection_evaluation()
    print("=" * 60)
    print(" CareSentry Guard Prompt-Injection Evaluation Results")
    print("=" * 60)
    for k, v in results.items():
        print(f" {k:<25}: {v}")
    print("=" * 60)
