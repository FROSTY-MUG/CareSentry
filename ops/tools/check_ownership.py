"""Ownership check: fails if a lane's diff touches a path it doesn't own.

Reads ops/ownership.json (master plan §4) and compares against the current
git diff.  Read-only for other lanes.

Usage:
    python ops/tools/check_ownership.py            # check staged + unstaged
    python ops/tools/check_ownership.py --staged   # staged only
    python ops/tools/check_ownership.py --branch   # diff against main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_FILE = REPO_ROOT / "ops" / "ownership.json"


def load_ownership() -> Dict[str, List[str]]:
    with open(OWNERSHIP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("lanes", {})


def get_changed_files(staged_only: bool = False, branch: str = "main") -> List[str]:
    """Return list of changed files relative to the given base."""
    if branch:
        cmd = ["git", "diff", "--name-only", f"{branch}...HEAD"]
    elif staged_only:
        cmd = ["git", "diff", "--name-only", "--cached"]
    else:
        cmd = ["git", "diff", "--name-only"]
    try:
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return files
    except Exception:
        return []


def check_ownership(
    files: List[str], ownership: Dict[str, List[str]], lane: str
) -> Tuple[List[str], List[str]]:
    """Returns (violations, warnings)."""
    violations: List[str] = []
    warnings: List[str] = []

    for f in files:
        # Check if this file falls under any lane's ownership
        matched = False
        for lane_name, paths in ownership.items():
            for pattern in paths:
                if f.startswith(pattern) or pattern in f:
                    matched = True
                    if lane_name != lane:
                        violations.append(
                            f"{f}: touched by {lane}, owned by {lane_name}"
                        )
                    break
            if matched:
                break
        if not matched:
            warnings.append(f"{f}: no lane claims ownership")
    return violations, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check lane ownership of changed files")
    parser.add_argument("--staged", action="store_true", help="Check staged files only")
    parser.add_argument("--branch", default="main", help="Base branch for diff (default: main)")
    parser.add_argument("--lane", default="studio", help="Current lane name")
    args = parser.parse_args()

    ownership = load_ownership()
    files = get_changed_files(staged_only=args.staged, branch=args.branch)
    if not files:
        print("No changed files detected.")
        return 0

    violations, warnings = check_ownership(files, ownership, args.lane)

    print(f"Checking {len(files)} changed files for lane '{args.lane}':")
    for f in files:
        print(f"  {f}")

    if violations:
        print("\nOWNERSHIP VIOLATIONS:")
        for v in violations:
            print(f"  FAIL: {v}")
        return 1

    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  WARN: {w}")

    print("\nOwnership check PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())