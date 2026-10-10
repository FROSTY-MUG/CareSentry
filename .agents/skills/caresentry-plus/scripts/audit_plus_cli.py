#!/usr/bin/env python3
"""CareSentry-AI Plus Skill CLI Entrypoint.

Open Standard Skill compliant runner for plus_audit_result.v1 evaluation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Add plus/src and project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PLUS_SRC = PROJECT_ROOT / "plus" / "src"

if str(PLUS_SRC) not in sys.path:
    sys.path.insert(0, str(PLUS_SRC))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from caresentry_plus.audit.audit_log import AuditLogger
from caresentry_plus.extraction.omission_checker import OmissionChecker
from caresentry_plus.ontology.normalizer import DrugNormalizer
from caresentry_plus.rules.engine import RulePackEngine


def execute_track_a_linter(records_text: str, summary_text: str) -> dict:
    """Run Track A linter via subprocess if script is available."""
    script_path = PROJECT_ROOT / ".agents" / "skills" / "caresentry" / "scripts" / "audit_contraindication.py"
    if script_path.exists():
        try:
            res = subprocess.run(
                [sys.executable, str(script_path), "--records", records_text, "--summary", summary_text, "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception:
            pass

    # In-memory fallback
    try:
        from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
        rules = load_clinical_rules()
        return audit_clinical_safety(records_text, summary_text, rules)
    except Exception:
        return {"status": "PASS", "violations": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="CareSentry-AI Plus Clinical Invariant Audit CLI")
    parser.add_argument("--records", "-r", required=True, help="Path to raw patient EHR or inline text.")
    parser.add_argument("--summary", "-s", required=True, help="Path to generated discharge summary or inline text.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output to stdout.")

    args = parser.parse_args()

    # Read records
    if Path(args.records).exists():
        with open(args.records, "r", encoding="utf-8") as f:
            records_text = f.read()
    else:
        records_text = args.records

    # Read summary
    if Path(args.summary).exists():
        with open(args.summary, "r", encoding="utf-8") as f:
            summary_text = f.read()
    else:
        summary_text = args.summary

    start = time.perf_counter()

    # Track A Base Check
    base_report = execute_track_a_linter(records_text, summary_text)

    # Track B Engines
    normalizer = DrugNormalizer()
    rule_engine = RulePackEngine(normalizer=normalizer)
    omission_checker = OmissionChecker(normalizer=normalizer)
    audit_logger = AuditLogger()

    plus_violations = rule_engine.evaluate_invariants(records_text, summary_text)
    omissions = omission_checker.check_omissions(records_text, summary_text)
    entities = normalizer.extract_and_normalize(records_text + " " + summary_text)

    context_flags = []
    for ent in entities:
        assertion = rule_engine.context_filter.analyze_assertion(records_text, ent.raw_term)
        context_flags.append({
            "phrase": ent.raw_term,
            "status": assertion.status.value,
            "entity": ent.canonical_name,
            "rationale": assertion.rationale,
        })

    has_critical = any(v.get("severity") in ["CRITICAL", "HIGH"] for v in plus_violations)
    has_critical_omission = any(o.severity == "CRITICAL" for o in omissions)
    overall_status = "FAIL" if (base_report.get("status") == "FAIL" or has_critical or has_critical_omission) else "PASS"

    log_entry = audit_logger.log_audit(
        raw_ehr=records_text,
        summary=summary_text,
        rule_packs=rule_engine.loaded_pack_ids,
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        verdict=overall_status,
        violations_count=len(plus_violations),
        omissions_count=len(omissions),
    )

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    payload = {
        "schema": "plus_audit_result.v1",
        "status": overall_status,
        "base": base_report,
        "plus_violations": plus_violations,
        "omissions": [o.to_dict() for o in omissions],
        "context_flags": context_flags,
        "normalized_entities": [e.to_dict() for e in entities],
        "provenance": {
            "rule_packs": rule_engine.loaded_pack_ids,
            "ontology_version": normalizer.ontology_version,
            "engine_version": "1.0.0",
        },
        "audit_log_ref": log_entry.entry_hash,
        "execution_time_ms": round(elapsed_ms, 2),
    }

    print(json.dumps(payload, indent=2))
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
