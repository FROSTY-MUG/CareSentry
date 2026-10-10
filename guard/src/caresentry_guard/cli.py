"""CareSentry Guard Unified CLI Entry Point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Bootstrap sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GUARD_SRC = Path(__file__).resolve().parent.parent
if str(GUARD_SRC) not in sys.path:
    sys.path.insert(0, str(GUARD_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from caresentry_guard.adapters.a_linter import LinterAdapter
from caresentry_guard.adapters.a_probe import ProbeAdapter
from caresentry_guard.adapters.a_runner import RunnerAdapter
from caresentry_guard.fingerprint.safety_card import PositionBiasFingerprinter
from caresentry_guard.grounding.engine import EvidenceGroundingEngine
from caresentry_guard.injection.scanner import ClinicalInjectionScanner
from caresentry_guard.packs.patient_pack import PatientPackGenerator
from caresentry_guard.policy.engine import SafetyPolicyEngine
from caresentry_guard.probes.linear_probe import HiddenStateProber


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="caresentry-guard",
        description="CareSentry Guard: Invariant Safety, Prompt-Injection & Grounding CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. audit
    audit_parser = subparsers.add_parser("audit", help="Run full guarded clinical audit")
    audit_parser.add_argument("--records", "-r", required=True, help="Path to raw clinical EHR record file or text")
    audit_parser.add_argument("--summary", "-s", required=True, help="Path to generated summary file or text")
    audit_parser.add_argument("--json", action="store_true", help="Emit raw JSON only")

    # 2. scan-injection
    inj_parser = subparsers.add_parser("scan-injection", help="Scan document for adversarial injections")
    inj_parser.add_argument("--doc", "-d", required=True, help="Path to document file or text string")
    inj_parser.add_argument("--json", action="store_true", help="Emit JSON only")

    # 3. patient-pack
    pack_parser = subparsers.add_parser("patient-pack", help="Generate verified patient output pack")
    pack_parser.add_argument("--summary", "-s", required=True, help="Verified summary text or file")
    pack_parser.add_argument("--patient", default="Patient", help="Patient name")
    pack_parser.add_argument("--html-out", help="Export large-print HTML file")

    # 4. fingerprint
    fp_parser = subparsers.add_parser("fingerprint", help="Generate Context Safety Card")
    fp_parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Target model ID")
    fp_parser.add_argument("--out", help="Export markdown file path")

    # 5. probe-causal
    probe_parser = subparsers.add_parser("probe-causal", help="Run causal linear probe study")
    probe_parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Model ID")

    # 6. serve
    serve_parser = subparsers.add_parser("serve", help="Run local OpenAI-compatible safety gateway")
    serve_parser.add_argument("--port", type=int, default=8787, help="Port (default: 8787)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")

    args = parser.parse_args()

    if args.command == "audit":
        ehr = Path(args.records).read_text(encoding="utf-8") if os.path.exists(args.records) else args.records
        summary = Path(args.summary).read_text(encoding="utf-8") if os.path.exists(args.summary) else args.summary

        linter = LinterAdapter()
        scanner = ClinicalInjectionScanner()
        grounder = EvidenceGroundingEngine()
        policy = SafetyPolicyEngine()

        linter_rep = linter.audit(ehr, summary)
        inj_rep = scanner.scan(summary)
        ground_rep = grounder.audit_grounding(ehr, summary)

        decision = policy.evaluate(
            raw_summary=summary,
            linter_status=linter_rep.status,
            linter_violations=linter_rep.violations,
            injection_detected=inj_rep.has_injection,
            injection_findings=inj_rep.findings,
            grounding_score=ground_rep.overall_grounding_score,
            safety_critical_violations=ground_rep.safety_critical_violations,
        )

        output = {
            "guard_version": "1.0.0",
            "policy_decision": decision.to_dict(),
            "clinical_linter": linter_rep.to_dict(),
            "injection_audit": {
                "has_injection": inj_rep.has_injection,
                "findings": [f.explanation for f in inj_rep.findings],
            },
            "grounding_audit": ground_rep.to_dict(),
        }

        if args.json:
            print(json.dumps(output, indent=2))
        else:
            print("=" * 65)
            print(" CareSentry Guard Clinical Audit Report")
            print("=" * 65)
            print(f" Policy State        : {decision.state.value}")
            print(f" Safe to Release     : {decision.is_safe_to_release}")
            print(f" Escalate to Human   : {decision.escalate_to_human}")
            print(f" Linter Status       : {linter_rep.status} ({linter_rep.total_violations} violations)")
            print(f" Injection Detected  : {inj_rep.has_injection}")
            print(f" Grounding Score     : {ground_rep.overall_grounding_score:.2f}")
            print("=" * 65)

        return 0 if decision.is_safe_to_release else 1

    elif args.command == "scan-injection":
        doc = Path(args.doc).read_text(encoding="utf-8") if os.path.exists(args.doc) else args.doc
        scanner = ClinicalInjectionScanner()
        res = scanner.scan(doc)
        if args.json:
            print(json.dumps({
                "has_injection": res.has_injection,
                "action_taken": res.action_taken,
                "zero_width_count": res.zero_width_count,
                "homoglyphs_detected": res.homoglyphs_detected,
                "findings": [f.explanation for f in res.findings],
            }, indent=2))
        else:
            print(f"Injection Detected: {res.has_injection} (Action: {res.action_taken})")
            for f in res.findings:
                print(f" - [{f.rule_id}] {f.explanation}")
        return 0 if not res.has_injection else 1

    elif args.command == "patient-pack":
        summary = Path(args.summary).read_text(encoding="utf-8") if os.path.exists(args.summary) else args.summary
        gen = PatientPackGenerator()
        pack = gen.generate_pack(summary, patient_name=args.patient)
        if args.html_out:
            Path(args.html_out).write_text(pack.large_print_html, encoding="utf-8")
            print(f"Exported large-print HTML pack to {args.html_out}")
        print(f"Readability Grade Level: Grade {pack.flesch_kincaid_grade_level} (Ease: {pack.reading_ease_score}/100)")
        return 0

    elif args.command == "fingerprint":
        fp = PositionBiasFingerprinter(model_id=args.model)
        card = fp.sweep()
        md = card.render_markdown()
        if args.out:
            Path(args.out).write_text(md, encoding="utf-8")
            print(f"Exported Context Safety Card to {args.out}")
        else:
            print(md)
        return 0

    elif args.command == "probe-causal":
        prober = HiddenStateProber(model_id=args.model)
        res = prober.run_causal_study()
        print(json.dumps(res.to_dict(), indent=2))
        return 0

    elif args.command == "serve":
        import uvicorn
        from caresentry_guard.gateway.server import app
        print(f"Starting CareSentry Guard Gateway at http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
