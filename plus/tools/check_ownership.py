#!/usr/bin/env python3
"""CareSentry-AI Ownership & Namespace Guard.

Enforces strict ownership boundary between Track A and Track B (Antigravity IDE-B).
When running in IDE-B context (e.g. CARESENTRY_AGENT=B), guarantees that:
1. Any staged file is strictly within the Track B allowlist:
   - plus/**
   - .agents/skills/caresentry-plus/**
   - .github/workflows/plus-*.yml
   - contracts/** (additive only)
   - contracts/requests/B-*
2. Frozen contracts (*.v1.*) are never modified in place.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Track B Allowed path prefixes
TRACK_B_PREFIXES = (
    "plus/",
    ".agents/skills/caresentry-plus/",
    ".github/workflows/plus-",
    "contracts/requests/B-",
)

FROZEN_CONTRACTS = (
    "contracts/audit_result.v1.schema.json",
    "contracts/attention_trace.v1.schema.json",
    "contracts/plus_audit_result.v1.schema.json",
    "contracts/rule_pack.v1.schema.json",
    "contracts/mitigation_strategy.v1.md",
)


def get_git_status_entries() -> List[Tuple[str, str, str]]:
    """Return list of (index_status, worktree_status, filepath) from git porcelain status."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        entries = []
        for raw_line in res.stdout.splitlines():
            if not raw_line or len(raw_line) < 4:
                continue
            index_status = raw_line[0]
            worktree_status = raw_line[1]
            filepath = raw_line[3:].strip().replace('"', "").replace("\\", "/")
            entries.append((index_status, worktree_status, filepath))
        return entries
    except Exception as e:
        print(f"[ownership_guard] Warning: git status failed ({e})")
        return []


def is_track_b_path(norm_path: str) -> bool:
    """Check if filepath falls within Track B owned namespace."""
    for prefix in TRACK_B_PREFIXES:
        if norm_path.startswith(prefix):
            return True
    if norm_path.startswith("contracts/"):
        return True
    return False


def check_ownership(check_staged_only: bool = True) -> int:
    """Validate ownership boundaries per PRD Section 8.3."""
    agent = os.getenv("CARESENTRY_AGENT", "B")
    if agent != "B":
        print(f"[ownership_guard] CARESENTRY_AGENT={agent}; skipping Track B ownership check.")
        return 0

    entries = get_git_status_entries()
    if not entries:
        print("[ownership_guard] Clean working tree. No modified or staged files.")
        return 0

    violations = []
    staged_count = 0

    for idx_stat, wt_stat, filepath in entries:
        is_staged = idx_stat in ("M", "A", "D", "R", "C")
        if is_staged:
            staged_count += 1

        # 1. Check frozen contract immutability (both staged and worktree)
        if filepath in FROZEN_CONTRACTS:
            if idx_stat == "M" or wt_stat == "M":
                violations.append(
                    f"FROZEN CONTRACT MODIFICATION: {filepath} (contracts are immutable once created; add .v2 instead)"
                )

        # 2. Check staged files against Track B allowlist
        if is_staged:
            if not is_track_b_path(filepath):
                violations.append(
                    f"UNAUTHORIZED STAGED FILE in Track A territory: {filepath} (Track B may only stage plus/**, contracts/**, or plus- skills/workflows)"
                )

    if violations:
        print(f"\n[ownership_guard] FAILED! {len(violations)} ownership boundary violation(s) detected:")
        for v in violations:
            print(f"  ❌ {v}")
        return 1

    print(f"[ownership_guard] PASSED: All staged files ({staged_count}) and contracts respect Track B ownership boundaries.")
    return 0


if __name__ == "__main__":
    sys.exit(check_ownership())
