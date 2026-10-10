"""MCP Server (F-12)

Provides Model Context Protocol (MCP) server over stdio.
Tools provided:
- audit: runs clinical linter
- normalize_drugs: normalizes drug names
- omission_check: checks for missing constraints
- render_heatmap: generates heatmap HTML
"""

import sys
import json
from harness.clinical_linter import audit_clinical_safety, load_clinical_rules

def handle_request(request: dict) -> dict:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "audit",
                        "description": "Run deterministic clinical safety audit on EHR and summary",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "records": {"type": "string"},
                                "summary": {"type": "string"}
                            },
                            "required": ["records", "summary"]
                        }
                    },
                    {
                        "name": "render_heatmap",
                        "description": "Render HTML attention heatmap from trace data",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "trace_data": {"type": "object"}
                            },
                            "required": ["trace_data"]
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "audit":
            rules = load_clinical_rules()
            report = audit_clinical_safety(args.get("records", ""), args.get("summary", ""), rules)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(report, indent=2)}]
                }
            }

        elif tool_name == "render_heatmap":
            from caresentry_studio.viz.heatmap import render_heatmap_html
            html = render_heatmap_html(args.get("trace_data", {}))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": html}]
                }
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": "Method not found"}
    }

def main():
    # Read stdio loop
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
