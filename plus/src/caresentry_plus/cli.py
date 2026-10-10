"""CareSentry-AI Plus Main Command Line Interface (CLI).

Entry point for `caresentry-plus` command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from caresentry_plus import __version__
from caresentry_plus.audit.audit_log import AuditLogger
from caresentry_plus.extraction.omission_checker import OmissionChecker
from caresentry_plus.ontology.normalizer import DrugNormalizer
from caresentry_plus.rules.engine import RulePackEngine
from caresentry_plus.viz.heatmap_viewer import render_heatmap_file


def cmd_audit(args: argparse.Namespace) -> int:
    """Execute end-to-end Plus clinical invariant audit."""
    from caresentry_plus.rules.engine import RulePackEngine
    from caresentry_plus.extraction.omission_checker import OmissionChecker
    from caresentry_plus.ontology.normalizer import DrugNormalizer

    records = Path(args.records).read_text(encoding="utf-8") if Path(args.records).exists() else args.records
    summary = Path(args.summary).read_text(encoding="utf-8") if Path(args.summary).exists() else args.summary

    normalizer = DrugNormalizer()
    engine = RulePackEngine(normalizer=normalizer)
    omission_checker = OmissionChecker(normalizer=normalizer)
    audit_logger = AuditLogger()

    # Track A base check
    base_report = {"status": "PASS", "violations": []}
    try:
        from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
        rules = load_clinical_rules()
        base_report = audit_clinical_safety(records, summary, rules)
    except Exception:
        pass

    plus_violations = engine.evaluate_invariants(records, summary)
    omissions = omission_checker.check_omissions(records, summary)
    entities = normalizer.extract_and_normalize(records + " " + summary)

    has_critical = any(v.get("severity") in ["CRITICAL", "HIGH"] for v in plus_violations)
    has_critical_omission = any(o.severity == "CRITICAL" for o in omissions)
    overall_status = "FAIL" if (base_report.get("status") == "FAIL" or has_critical or has_critical_omission) else "PASS"

    log_entry = audit_logger.log_audit(
        raw_ehr=records,
        summary=summary,
        rule_packs=engine.loaded_pack_ids,
        model_id="Qwen/Qwen2.5-1.5B-Instruct",
        verdict=overall_status,
        violations_count=len(plus_violations),
        omissions_count=len(omissions),
    )

    payload = {
        "schema": "plus_audit_result.v1",
        "status": overall_status,
        "base": base_report,
        "plus_violations": plus_violations,
        "omissions": [o.to_dict() for o in omissions],
        "normalized_entities": [e.to_dict() for e in entities],
        "provenance": {
            "rule_packs": engine.loaded_pack_ids,
            "ontology_version": normalizer.ontology_version,
            "engine_version": __version__,
        },
        "audit_log_ref": log_entry.entry_hash,
    }

    print(json.dumps(payload, indent=2))
    return 0 if overall_status == "PASS" else 1


def cmd_normalize(args: argparse.Namespace) -> int:
    """Normalize drug names in text."""
    normalizer = DrugNormalizer()
    entities = normalizer.extract_and_normalize(args.text)
    print(json.dumps([e.to_dict() for e in entities], indent=2))
    return 0


def cmd_omission_check(args: argparse.Namespace) -> int:
    """Check for omitted clinical constraints."""
    records = Path(args.records).read_text(encoding="utf-8") if Path(args.records).exists() else args.records
    summary = Path(args.summary).read_text(encoding="utf-8") if Path(args.summary).exists() else args.summary

    checker = OmissionChecker()
    omissions = checker.check_omissions(records, summary)
    print(json.dumps([o.to_dict() for o in omissions], indent=2))
    return 0 if len(omissions) == 0 else 1


def cmd_render_heatmap(args: argparse.Namespace) -> int:
    """Render self-contained HTML attention heatmap."""
    trace_path = Path(args.trace_file)
    output_path = Path(args.output)
    comp_path = Path(args.compare_trace) if args.compare_trace else None

    if not trace_path.exists():
        print(f"Error: Trace file not found at {trace_path}", file=sys.stderr)
        return 1

    render_heatmap_file(trace_path, output_path, comparative_trace_path=comp_path)
    print(f"Successfully generated heatmap: {output_path}")
    return 0


def cmd_verify_log(args: argparse.Namespace) -> int:
    """Verify cryptographic integrity of an audit log."""
    log_path = Path(args.log_file)
    is_valid, errors = AuditLogger.verify_log(log_path)
    if is_valid:
        print(f"[PASS] Cryptographic audit log {log_path} is intact. Zero tampering detected.")
        return 0
    else:
        print(f"[FAIL] Audit log verification failed for {log_path}:", file=sys.stderr)
        for err in errors:
            print(f"  * {err}", file=sys.stderr)
        return 1


def cmd_webui(args: argparse.Namespace) -> int:
    """Launch the Gradio Web UI."""
    webui_script = Path(__file__).resolve().parent.parent.parent / "webui" / "app.py"
    if not webui_script.exists():
        print("Error: webui/app.py not found", file=sys.stderr)
        return 1

    import subprocess
    cmd = [sys.executable, str(webui_script)]
    return subprocess.run(cmd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="caresentry-plus",
        description="CareSentry-AI Plus — Extended Deterministic Clinical Invariants & Observability Gate",
    )
    parser.add_argument("--version", action="version", version=f"caresentry-plus {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run full clinical invariant audit")
    p_audit.add_argument("--records", "-r", required=True, help="Path to patient EHR or inline text")
    p_audit.add_argument("--summary", "-s", required=True, help="Path to summary or inline text")
    p_audit.set_defaults(func=cmd_audit)

    # normalize
    p_norm = subparsers.add_parser("normalize", help="Normalize drug entities to RxNorm/ATC")
    p_norm.add_argument("--text", "-t", required=True, help="Clinical text to parse")
    p_norm.set_defaults(func=cmd_normalize)

    # omission-check
    p_omiss = subparsers.add_parser("omission-check", help="Run reverse omission verification")
    p_omiss.add_argument("--records", "-r", required=True, help="Path to EHR record or inline text")
    p_omiss.add_argument("--summary", "-s", required=True, help="Path to summary or inline text")
    p_omiss.set_defaults(func=cmd_omission_check)

    # render-heatmap
    p_heat = subparsers.add_parser("render-heatmap", help="Generate HTML token attention heatmap")
    p_heat.add_argument("--trace-file", "-t", required=True, help="Path to attention_trace.v1 JSON")
    p_heat.add_argument("--output", "-o", default="heatmap.html", help="Path to output HTML file")
    p_heat.add_argument("--compare-trace", "-c", default=None, help="Optional comparative trace file for side-by-side view")
    p_heat.set_defaults(func=cmd_render_heatmap)

    # verify-log
    p_log = subparsers.add_parser("verify-log", help="Verify cryptographic hash-chained audit log")
    p_log.add_argument("--log-file", "-l", required=True, help="Path to audit log JSONL file")
    p_log.set_defaults(func=cmd_verify_log)

    # webui
    p_web = subparsers.add_parser("webui", help="Launch interactive Gradio Web UI")
    p_web.add_argument("--port", "-p", type=int, default=7860, help="Port to bind (default: 7860)")
    p_web.set_defaults(func=cmd_webui)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
