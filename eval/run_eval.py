"""run_eval.py

Runs the evaluation suite on the generated synthetic cases.
Computes metrics and saves results in eval/results/

Usage:
    python eval/run_eval.py --deterministic
"""

import argparse
import json
from pathlib import Path
from eval.metrics import compute_metrics
from harness.attention_probe import AttentionProbe
from harness.clinical_linter import audit_clinical_safety, load_clinical_rules

def run_evaluation(model_id: str, case_file: Path):
    with open(case_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    rules = load_clinical_rules()
    results = []
    
    print(f"Running evaluation on {len(cases)} cases...")
    
    probe = AttentionProbe(model_id=model_id)

    for case in cases:
        # Run audit
        report = audit_clinical_safety(case["context"], case["summary"], rules)
        
        # Run probe
        probe_result = probe.probe(prompt=case["context"], needle=case["needle"])
        
        # Aggregate result
        results.append({
            "case_id": case["id"],
            "has_violation": case["include_violation"],
            "violation_detected": report["status"] == "FAIL",
            "mitigation_triggered": probe_result.mitigation_triggered,
            "rescued": probe_result.mitigation_triggered and probe_result.classification == "SUFFICIENTLY_ATTENDED",
            "z_score": probe_result.z_score,
            "raw_audit": report
        })
        
    metrics = compute_metrics(results)
    return results, metrics

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--deterministic", action="store_true")
    args = parser.parse_args()
    
    case_file = Path("eval") / "data" / "synthetic_cases_100.json"
    results, metrics = run_evaluation(args.model, case_file)
    
    # Save results
    results_file = Path("eval") / "results" / f"eval_{args.model.replace('/', '_')}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    output = {
        "model": args.model,
        "metrics": metrics,
        "results": results
    }
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
    print(f"Results saved to {results_file}")
    print(f"Metrics: {json.dumps(metrics, indent=2)}")

if __name__ == "__main__":
    main()
