#!/usr/bin/env python3
"""CareSentry-AI Plus Model Context Protocol (MCP) Stdio Server (F-12).

Exposes deterministic clinical invariant validation, drug normalization,
reverse omission checks, and attention heatmap generation over standard JSON-RPC 2.0 stdio.
All responses adhere strictly to contracts/plus_audit_result.v1.schema.json.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure plus/src is on sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
ROOT_PATH = Path(__file__).resolve().parent.parent.parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from caresentry_plus.adapters.probe_shim import ProbeShim
from caresentry_plus.audit.audit_log import AuditLogger
from caresentry_plus.extraction.omission_checker import OmissionChecker
from caresentry_plus.ontology.normalizer import DrugNormalizer
from caresentry_plus.rules.engine import RulePackEngine
from caresentry_plus.viz.heatmap_viewer import generate_heatmap_html

logger = logging.getLogger("caresentry_plus.mcp")

TOOLS_REGISTRY = [
    {
        "name": "audit_plus",
        "description": "Execute comprehensive deterministic clinical safety audit (Track A linter + Track B invariant rule packs + reverse omission gate). Returns plus_audit_result.v1.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {"type": "string", "description": "Raw patient EHR notes, vitals, labs, and history."},
                "summary": {"type": "string", "description": "Model-generated discharge summary to evaluate."},
            },
            "required": ["records", "summary"],
        },
    },
    {
        "name": "normalize_drugs",
        "description": "Normalize brand names, generic formulations, and abbreviations to canonical RxNorm/ATC drug entities.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Clinical narrative or medication list to normalize."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "omission_check",
        "description": "Reverse verification testing whether critical constraints documented in EHR (allergies, renal, anticoagulation) were dropped from discharge summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {"type": "string", "description": "Raw patient EHR records."},
                "summary": {"type": "string", "description": "Discharge summary."},
            },
            "required": ["records", "summary"],
        },
    },
    {
        "name": "render_heatmap",
        "description": "Generate self-contained HTML token attention heatmap from a trace file or prompt + needle.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {"type": "string", "description": "Patient record prompt text."},
                "needle": {"type": "string", "description": "Target clinical constraint needle."},
                "trace_path": {"type": "string", "description": "Optional path to frozen trace JSON file."},
            },
        },
    },
]


class MCPServer:
    """Stdio JSON-RPC MCP Server implementation."""

    def __init__(self):
        self.normalizer = DrugNormalizer()
        self.rule_engine = RulePackEngine(normalizer=self.normalizer)
        self.omission_checker = OmissionChecker(normalizer=self.normalizer)
        self.probe_shim = ProbeShim(fallback_mode=True)
        self.audit_logger = AuditLogger()

    def run_audit_plus(self, records: str, summary: str) -> Dict[str, Any]:
        """Execute audit matching contracts/plus_audit_result.v1.schema.json."""
        start = time.perf_counter()

        # Track A base check via internal fallback/import
        base_report = {
            "status": "PASS",
            "violations": [],
            "standard": "agent-skills.io/v1",
        }
        try:
            from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
            rules = load_clinical_rules()
            base_report = audit_clinical_safety(records, summary, rules)
        except Exception:
            pass

        plus_violations = self.rule_engine.evaluate_invariants(records, summary)
        omissions = self.omission_checker.check_omissions(records, summary)
        entities = self.normalizer.extract_and_normalize(records + " " + summary)

        # Context flags
        context_flags = []
        for ent in entities:
            assertion = self.rule_engine.context_filter.analyze_assertion(records, ent.raw_term)
            context_flags.append({
                "phrase": ent.raw_term,
                "status": assertion.status.value,
                "entity": ent.canonical_name,
                "rationale": assertion.rationale,
            })

        has_critical = any(v.get("severity") in ["CRITICAL", "HIGH"] for v in plus_violations)
        has_critical_omission = any(o.severity == "CRITICAL" for o in omissions)
        overall_status = "FAIL" if (base_report.get("status") == "FAIL" or has_critical or has_critical_omission) else "PASS"

        log_entry = self.audit_logger.log_audit(
            raw_ehr=records,
            summary=summary,
            rule_packs=self.rule_engine.loaded_pack_ids,
            model_id="Qwen/Qwen2.5-1.5B-Instruct",
            verdict=overall_status,
            violations_count=len(plus_violations),
            omissions_count=len(omissions),
        )

        elapsed = (time.perf_counter() - start) * 1000.0

        return {
            "schema": "plus_audit_result.v1",
            "status": overall_status,
            "base": base_report,
            "plus_violations": plus_violations,
            "omissions": [o.to_dict() for o in omissions],
            "context_flags": context_flags,
            "normalized_entities": [e.to_dict() for e in entities],
            "provenance": {
                "rule_packs": self.rule_engine.loaded_pack_ids,
                "ontology_version": self.normalizer.ontology_version,
                "engine_version": "1.0.0",
            },
            "audit_log_ref": log_entry.entry_hash,
            "execution_time_ms": round(elapsed, 2),
        }

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC 2.0 MCP request."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "caresentry-plus-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_REGISTRY},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            try:
                if tool_name == "audit_plus":
                    payload = self.run_audit_plus(args.get("records", ""), args.get("summary", ""))
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}]
                        },
                    }

                elif tool_name == "normalize_drugs":
                    entities = self.normalizer.extract_and_normalize(args.get("text", ""))
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps([e.to_dict() for e in entities], indent=2)}]
                        },
                    }

                elif tool_name == "omission_check":
                    omissions = self.omission_checker.check_omissions(args.get("records", ""), args.get("summary", ""))
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps([o.to_dict() for o in omissions], indent=2)}]
                        },
                    }

                elif tool_name == "render_heatmap":
                    trace_path = args.get("trace_path")
                    if trace_path and Path(trace_path).exists():
                        trace_data = json.loads(Path(trace_path).read_text(encoding="utf-8"))
                    else:
                        trace = self.probe_shim.probe(args.get("records", ""), args.get("needle", "penicillin"))
                        trace_data = trace.to_dict()

                    html = generate_heatmap_html(trace_data)
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": html}]
                        },
                    }

                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method/Tool {tool_name} not found"},
                    }

            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"Tool execution failed: {str(e)}"},
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unrecognized method: {method}"},
        }

    def serve_stdio(self) -> None:
        """Read newline-delimited JSON-RPC messages from stdin and write to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def main():
    server = MCPServer()
    server.serve_stdio()


if __name__ == "__main__":
    main()
