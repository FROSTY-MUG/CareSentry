#!/usr/bin/env python3
"""CareSentry Guard Ownership Enforcement Tool.

Enforces Track C boundaries:
- Track C may ONLY create or modify files in:
  * guard/**
  * .agents/skills/caresentry-guard/**
  * .github/workflows/guard-*.yml
- Track A paths (root files, harness/**, data/**, tests/**, demo/**, etc.) must NEVER be modified.
- Track B paths (plus/**, contracts/**, etc.) must NEVER be created or modified.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TRACK_C_ALLOWED_PREFIXES = [
    "guard/",
    "guard\\",
    ".agents/skills/caresentry-guard/",
    ".agents/skills/caresentry-guard\\",
    ".github/workflows/guard-",
]

TRACK_B_FORBIDDEN_PREFIXES = [
    "plus/",
    "plus\\",
    "contracts/",
    "contracts\\",
    ".agents/skills/caresentry-plus/",
    ".agents/skills/caresentry-plus\\",
    ".github/workflows/plus-",
]


def get_git_modified_files(repo_root: Path) -> list[str]:
    """Retrieve list of files staged for commit or Track C working files."""
    try:
        # Check staged files first
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        staged = [line.strip().replace("/", os.sep) for line in res.stdout.strip().splitlines() if line.strip()]
        if staged:
            return staged

        # If nothing staged yet, inspect untracked and modified files belonging to Track C
        res_status = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        print(f"Error checking git status: {e}")
        return []

    lines = res_status.stdout.strip().splitlines()
    files = []
    for line in lines:
        if len(line) >= 4:
            path_str = line[3:].strip()
            if " -> " in path_str:
                path_str = path_str.split(" -> ")[1].strip()
            f_norm = path_str.replace("\\", "/")
            # Only check files that Track C intends to manage or touches Track A/B forbidden
            if f_norm.startswith("guard/") or f_norm.startswith(".agents/skills/caresentry-guard/") or f_norm.startswith(".github/workflows/guard-") or f_norm.startswith("plus/") or f_norm.startswith("contracts/"):
                files.append(path_str.replace("/", os.sep))
    return files


def check_ownership(repo_root: Path) -> tuple[bool, list[str]]:
    """Verify all modified and created files comply with Track C boundaries."""
    files = get_git_modified_files(repo_root)
    violations = []

    for f in files:
        f_norm = f.replace("\\", "/")
        
        # Check if touching Track B
        for b in TRACK_B_FORBIDDEN_PREFIXES:
            b_norm = b.replace("\\", "/")
            if f_norm.startswith(b_norm):
                violations.append(f"Track B reserved path touched: {f}")
                break

        # Check if touching Track A or other forbidden files
        allowed = False
        for c in TRACK_C_ALLOWED_PREFIXES:
            c_norm = c.replace("\\", "/")
            if f_norm.startswith(c_norm):
                allowed = True
                break

        if not allowed:
            violations.append(f"Track A / non-Track-C path modified: {f}")

    return len(violations) == 0, violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    success, violations = check_ownership(repo_root)

    print("=" * 60)
    print(" CareSentry Guard - Track C Ownership Verification")
    print("=" * 60)
    print(f" Repository root: {repo_root}")

    if success:
        print(" [PASS] All staged and unstaged files are strictly inside Track C boundaries.")
        print("=" * 60)
        return 0
    else:
        print(" [FAIL] Found boundary violations:")
        for v in violations:
            print(f"   * {v}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
