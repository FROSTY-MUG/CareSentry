"""Integration Check Tool

Runs all suites and cross-lane smoke test. Used by CORE at every checkpoint.
Exits with 0 on success, non-zero on failure. Prints a one-page status report.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SUITES = {
    "studio": ["pytest", "studio/tests", "-q", "--tb=short"],
    "clinical": ["pytest", "clinical/tests", "-q", "--tb=short"],
    "guard": ["pytest", "guard/tests", "-q", "--tb=short"],
    "eval": ["python", "eval/run_eval.py", "--deterministic"],
    "benchmark": ["python", "ops/tools/render_tables.py"],
}


def run_command(cmd: list, name: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT: {name}", ""
    except Exception as e:
        return 1, f"ERROR: {name}: {e}", ""


def main() -> int:
    parser = argparse.ArgumentParser(description="CareSentry Integration Check")
    parser.add_argument("--skip-missing", action="store_true", help="Skip lanes that don't exist")
    args = parser.parse_args()

    print("=== CareSentry Integration Check ===")
    print(f"Run at: {datetime.datetime.now().isoformat()}")
    print()

    overall_status = 0
    lane_status = {}

    for lane, cmd in SUITES.items():
        print(f"--- {lane.upper()} ---")
        rc, out, err = run_command(cmd, lane)
        lane_status[lane] = rc
        if rc == 0:
            print("PASS")
            if out.strip():
                print(out.strip()[:200] + "..." if len(out.strip()) > 200 else out.strip())
        else:
            print(f"FAIL (exit {rc})")
            print(f"Stdout: {out.strip()[:200] if out.strip() else 'none'}")
            print(f"Stderr: {err.strip()[:200] if err.strip() else 'none'}")
            overall_status = rc
        print()

    # Cross-lane smoke test
    print("--- CROSS-LANE SMOKE TEST ---")
    # Test that each lane's CLI tools exist
    for lane in ["studio", "clinical", "guard"]:
        cli_path = REPO_ROOT / "studio" / "src" / "caresentry_studio" / "cli.py"
        if not cli_path.exists():
            print(f"FAIL: {lane} CLI not found")
            overall_status = 1
    print()

    # Summary
    print("=== SUMMARY ===")
    status_emoji = "✅" if overall_status == 0 else "❌"
    print(f"{status_emoji} Overall: {'PASS' if overall_status == 0 else 'FAIL'}")
    print(f"   Suites: {sum(1 for rc in lane_status.values() if rc == 0)}/{len(lane_status)} passed")
    print(f"   Skipped: {len([rc for rc in lane_status.values() if rc == 124])} timed out")
    print(f"   Missing: {len([rc for rc in lane_status.values() if rc == 127])} not found")
    print()
    print("Next steps:")
    if overall_status != 0:
        print("  - Fix failing suites before CP1")
    else:
        print("  - All suites green. Ready for CP1.")

    return overall_status


if __name__ == "__main__":
    sys.exit(main())
