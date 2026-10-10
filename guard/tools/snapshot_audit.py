#!/usr/bin/env python3
"""CareSentry Observer Audit Tool for Step 1 & Step 2.
Performs read-only inspection of all 4 lanes and worktrees.
"""

import datetime
import os
import subprocess
import sys
from pathlib import Path

LANES = {
    "core": {
        "agent": "Claude Code",
        "worktree": Path(r"C:\Users\HP\app\CareSentry-wt\core"),
        "branch": "lane/core",
        "notes": [Path(r"C:\Users\HP\app\CareSentry-wt\core\docs\LANE_NOTES_CORE.md"), Path(r"C:\Users\HP\app\CareSentry\docs\LANE_NOTES_CORE.md")],
        "test_cmd": ["pytest", "tests", "-q"],
        "cwd_test": Path(r"C:\Users\HP\app\CareSentry-wt\core"),
    },
    "guard": {
        "agent": "Codex / Antigravity",
        "worktree": Path(r"C:\Users\HP\app\CareSentry-wt\guard"),
        "fallback_worktree": Path(r"C:\Users\HP\app\CareSentry"),
        "branch": "lane/guard",
        "notes": [Path(r"C:\Users\HP\app\CareSentry\guard\docs\LANE_NOTES.md"), Path(r"C:\Users\HP\app\CareSentry-wt\guard\guard\docs\LANE_NOTES.md")],
        "test_cmd": ["pytest", "guard/tests", "-q"],
        "cwd_test": Path(r"C:\Users\HP\app\CareSentry"),
    },
    "clinical": {
        "agent": "OpenCode",
        "worktree": Path(r"C:\Users\HP\app\CareSentry-wt\clinical"),
        "fallback_worktree": Path(r"C:\Users\HP\app\CareSentry\clinical"),
        "branch": "lane/clinical",
        "notes": [Path(r"C:\Users\HP\app\CareSentry-wt\clinical\docs\LANE_NOTES.md"), Path(r"C:\Users\HP\app\CareSentry\clinical\docs\LANE_NOTES.md")],
        "test_cmd": ["pytest", "clinical/tests", "-q"],
        "cwd_test": Path(r"C:\Users\HP\app\CareSentry-wt\clinical"),
    },
    "studio": {
        "agent": "Hermes Agent",
        "worktree": Path(r"C:\Users\HP\app\CareSentry-wt\studio"),
        "fallback_worktree": Path(r"C:\Users\HP\app\CareSentry\studio"),
        "branch": "lane/studio",
        "notes": [Path(r"C:\Users\HP\app\CareSentry-wt\studio\docs\LANE_NOTES.md"), Path(r"C:\Users\HP\app\CareSentry\studio\docs\LANE_NOTES.md")],
        "test_cmd": ["pytest", "studio/tests", "-q"],
        "test_cmd_eval": ["pytest", "eval/tests", "-q"],
        "cwd_test": Path(r"C:\Users\HP\app\CareSentry-wt\studio"),
    },
}

def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=30)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def main():
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"=== OBSERVATION SNAPSHOT: {now_iso} ===")
    
    # Git origin status
    rc, remotes, _ = run_cmd(["git", "branch", "-r"], cwd=r"C:\Users\HP\app\CareSentry")
    print(f"\n--- Remote Branches ---\n{remotes}")

    rc, log3, _ = run_cmd(["git", "log", "--oneline", "origin/main", "-n", "5"], cwd=r"C:\Users\HP\app\CareSentry")
    print(f"\n--- origin/main last commits ---\n{log3}")

    rc, wt_list, _ = run_cmd(["git", "worktree", "list"], cwd=r"C:\Users\HP\app\CareSentry")
    print(f"\n--- git worktree list ---\n{wt_list}")

    for lane, info in LANES.items():
        print(f"\n==================== LANE: {lane.upper()} ({info['agent']}) ====================")
        wt = info["worktree"]
        if not wt.exists() and "fallback_worktree" in info and info["fallback_worktree"].exists():
            print(f"[NOTE] Expected worktree {wt} does not exist. Found at fallback: {info['fallback_worktree']}")
            active_wt = info["fallback_worktree"]
        else:
            active_wt = wt

        if not active_wt.exists():
            print(f"[STATUS] Worktree NOT FOUND at {wt}")
            continue

        print(f"Active Path: {active_wt}")
        _, status, _ = run_cmd(["git", "-C", str(active_wt), "status", "--short"])
        print(f"Status:\n{status if status else '(clean)'}")

        _, branch, _ = run_cmd(["git", "-C", str(active_wt), "branch", "--show-current"])
        print(f"Current Branch: {branch}")

        _, log5, _ = run_cmd(["git", "-C", str(active_wt), "log", "--oneline", "-n", "5"])
        print(f"Recent Commits:\n{log5}")

        _, log1_fmt, _ = run_cmd(["git", "-C", str(active_wt), "log", "-1", '--format=%cI %s'])
        print(f"Last Commit Date & Subject: {log1_fmt}")

        _, stash, _ = run_cmd(["git", "-C", str(active_wt), "stash", "list"])
        print(f"Stash:\n{stash if stash else '(none)'}")

        # Check lane notes
        found_notes = None
        for n in info["notes"]:
            if n.exists():
                found_notes = n
                break
        if found_notes:
            print(f"Lane Notes ({found_notes.name}): FOUND ({found_notes.stat().st_size} bytes)")
            preview = "\n".join(found_notes.read_text(encoding="utf-8", errors="ignore").splitlines()[:10])
            print(f"Preview:\n{preview}")
        else:
            print("Lane Notes: NOT FOUND")

        # Run tests if test dir exists
        test_cwd = active_wt if active_wt.exists() else info["cwd_test"]
        print(f"Running tests: {' '.join(info['test_cmd'])} in {test_cwd}")
        rc, out, err = run_cmd(info["test_cmd"], cwd=test_cwd)
        print(f"Test Result (rc={rc}): {out}")
        if err:
            print(f"Test Stderr: {err[:300]}")

        if "test_cmd_eval" in info:
            print(f"Running eval tests: {' '.join(info['test_cmd_eval'])} in {test_cwd}")
            rc_ev, out_ev, err_ev = run_cmd(info["test_cmd_eval"], cwd=test_cwd)
            print(f"Eval Test Result (rc={rc_ev}): {out_ev}")

if __name__ == "__main__":
    main()
