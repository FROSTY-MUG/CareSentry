"""Adapter to invoke the core CareSentry linter as a subprocess.

Complies with the clinical lane contract: parse JSON output from the core,
ignore unknown fields, and expose a simple Python API.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _find_linter_exe() -> Path:
    """Find the core linter script path."""
    # Prefer the package-internal runner, then fallback to direct import
    candidates = [
        Path(__file__).parent.parent.parent / "harness" / "clinical_linter.py",
        Path.cwd() / "harness" / "clinical_linter.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Could not locate core clinical_linter.py")


def _build_command(
    records: str,
    summary: str,
    rules: Optional[str] = None,
    json_output: bool = True,
) -> list[str]:
    """Build the CLI command to invoke the core linter."""
    cmd = [sys.executable, str(_find_linter_exe()), "--records", records, "--summary", summary]
    if rules:
        cmd.extend(["--rules", rules])
    if json_output:
        cmd.append("--json")
    return cmd


def audit(
    records: str,
    summary: str,
    rules: Optional[str] = None,
    json_output: bool = True,
) -> Dict[str, Any]:
    """Run the core linter and return parsed JSON result.

    Returns the full linter output dict. Unknown fields are silently
    dropped (extra entries in the JSON are retained but not accessed).
    """
    cmd = _build_command(records, summary, rules, json_output)
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = repo_root + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    env["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Linter timed out: {e}") from e

    if result.returncode in (0, 1) and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass

    # Direct in-process fallback if subprocess invocation encounters Windows CLI quoting or output issues
    try:
        from harness.clinical_linter import audit_clinical_safety, load_clinical_rules, parse_summary_payload
        summary_clean = parse_summary_payload(summary)
        active_rules = load_clinical_rules(rules)
        return audit_clinical_safety(records, summary_clean, active_rules)
    except Exception as exc:
        raise RuntimeError(
            f"Core linter failed (code {result.returncode}, stderr: {result.stderr}): {exc}"
        ) from exc


# Known output keys from the core linter standard (agent-skills.io/v1)
KNOWN_KEYS = {
    "status",
    "total_violations",
    "violations",
    "passed_checks_count",
    "passed_checks",
    "renal_metrics",
    "execution_time_ms",
    "standard",
}


def normalize_output(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Filter raw linter output to known keys only."""
    return {k: v for k, v in raw.items() if k in KNOWN_KEYS}


if __name__ == "__main__":
    # Allow running this adapter directly for ad-hoc debugging
    if len(sys.argv) < 3:
        print("Usage: python -m caresentry_clinical.adapters <records> <summary> [--rules <path>]")
        sys.exit(1)

    records_arg = sys.argv[1]
    summary_arg = sys.argv[2]
    rules_arg = None
    json_flag = True

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--rules" and i + 1 < len(sys.argv):
            rules_arg = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--no-json":
            json_flag = False
            i += 1
        else:
            i += 1

    try:
        data = audit(records_arg, summary_arg, rules_arg, json_flag)
        print(json.dumps(normalize_output(data), indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)