# CareSentry Status Overview

## 1. Snapshot Time and Project Checkpoint
- **Snapshot Time:** `2026-10-10T08:37:11Z` (Local: `2026-10-10T14:07:11+05:30`)
- **Project Checkpoint:** **Checkpoint 2 / Integration Window (Hour 16–24)**
  - *Evidence:* Track A (Core 1.1) and Track C (Guard UI & Gateway) PRs (#1 and #2) are merged into `origin/main`. Core deterministic invariant enhancements and Guard gateway UI endpoints are live. Track B features were merged to `main` under `plus/`, but worktrees and isolation branches for clinical and studio remain misaligned.

## 2. Overview Table

| Lane | Agent | Branch | Last Commit Time | Last Commit Subject | Tests | Status | Cause (if stuck) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CORE** | Claude Code | `lane/core` | 2026-10-10T14:05:56+05:30 | `[INT] repo setup: gitignore, workflow, repo state` | 23 passed (100%) | **ON TRACK** | None. Tests passing, active recent commit. |
| **GUARD** | Codex / Antigravity | `lane/guard` | 2026-10-10T13:32:23+05:30 | `[INT] repo setup: gitignore, workflow, repo state` | 31 passed (100%) | **ON TRACK** | None. Gateway and UI tests passing, merged to main via PR #1. |
| **CLINICAL** | OpenCode | *None* | *N/A* | *N/A* | 0 run (`clinical/tests` missing) | **STUCK** | Worktree `C:\Users\HP\app\CareSentry-wt\clinical` does not exist; branch `lane/clinical` is absent. Track B code exists under `plus/` instead of `clinical/`. |
| **STUDIO** | Hermes Agent | `lane/studio` | 2026-10-10T12:27:46+05:30 | `feat: initial release of CareSentry-AI v1.0.0-rc1` | 0 run (`studio/tests` missing) | **STUCK** | Worktree created at `CareSentry\studio` instead of `CareSentry-wt\studio`. Zero commits on `lane/studio` since baseline; uncommitted untracked work. |

## 3. Blocked Items and Ownership
1. **Clinical Lane Worktree & Adapter Isolation**:
   - *Blocked Item:* Guard and Core lanes cannot link against `clinical/` test suites or import standardized clinical modules.
   - *Owner:* OpenCode (CLINICAL lane).
   - *Action Required:* Create worktree `C:\Users\HP\app\CareSentry-wt\clinical` on branch `lane/clinical`, expose `clinical/tests`, and reconcile `plus/` vs `clinical/`.
2. **Studio Workbench Availability & Live Linking**:
   - *Blocked Item:* Guard Console UI footer links to port 7860 cannot resolve, and research audit benchmarks cannot run.
   - *Owner:* Hermes Agent (STUDIO lane).
   - *Action Required:* Relocate worktree to `C:\Users\HP\app\CareSentry-wt\studio`, commit staged components, and provide `studio/tests`.

## 4. Decisions Still Open (from FOLLOWUP_PRD_INTEGRATION.md)
- **D1 (Shared Contract vs Lane Directory Reconciliation):**
  - Clinical code currently resides under `plus/` (merged via commit `754006d`), whereas AGENTS_MASTER_PLAN and Track C specify `clinical/`. Needs final alignment across teams.
- **D3 (Telemetry Trace Schema Standard):**
  - Contracts exist in `contracts/attention_trace.v1.schema.json` and `contracts/requests/B-0001-dump-trace-flag.md`, but runtime consumption by Studio web UI is unverified due to lack of committed Studio tests.
- **D9 (Exit Code Uniformity across CLI Invocations):**
  - Contract request `contracts/requests/B-0002-cli-exit-codes.md` awaits verified multi-agent conformance testing in CI.

## 5. What Was NOT Verified, and Why
1. **GPU-Dependent Inference Runs**:
   - Live multi-head attention weights extraction and full 7B/9B model forward passes were not executed to avoid VRAM exhaustion on local hardware; simulated fallbacks and deterministic mocked passes were utilized.
2. **`docs/prds/FOLLOWUP_PRD_INTEGRATION.md` Content Directly**:
   - The specific file `docs/prds/FOLLOWUP_PRD_INTEGRATION.md` is not present on disk in `origin/main` or local worktrees; decisions D1, D3, D9 were identified from `contracts/` and `docs/REPO_STATE.md`.
3. **Studio WebUI Port 7860 Interaction**:
   - Studio web application was not launched due to uncommitted files and missing entrypoint tests in `lane/studio`.
