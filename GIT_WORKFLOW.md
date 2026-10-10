# CareSentry Git & Integration Workflow

**Author:** CORE Lane (Integrator)  
**Authority:** `AGENTS_MASTER_PLAN.md`, `FOLLOWUP_PRD_INTEGRATION.md`  
**Date:** 2026-10-10

---

## 1. Multi-Lane Workspace Layout

CareSentry is structured into 4 isolated lanes. Each lane operates within its own dedicated git worktree on its own branch:

| Lane | Branch | Worktree Path | Primary Focus |
|---|---|---|---|
| **CORE** (Integrator) | `lane/core` | `C:\Users\HP\app\CareSentry-wt\core` | Core engine, attention math, contracts, release integration |
| **GUARD** | `lane/guard` | `C:\Users\HP\app\CareSentry-wt\guard` | Safety guardrails, constrained decoding, de-identification |
| **CLINICAL** | `lane/clinical` | `C:\Users\HP\app\CareSentry-wt\clinical` | Clinical rule packs, EHR adapters, medical verification |
| **STUDIO** | `lane/studio` | `C:\Users\HP\app\CareSentry-wt\studio` | Web studio, benchmark dashboards, model fingerprinting |

### Ownership Boundaries
- **CORE:** `harness/**`, `contracts/**`, `data/**`, `tests/**`, `demo/**`, `.agents/skills/caresentry/**`, `.github/workflows/ci.yml`, root files.
- **GUARD:** `guard/**`, `.agents/skills/caresentry-guard/**`.
- **CLINICAL:** `clinical/**`, `.agents/skills/caresentry-clinical/**`.
- **STUDIO:** `studio/**`, `eval/**`, `ops/**`.

> **STRICT RULE:** No lane may write or commit files in another lane's path. Reads/tests of other lanes are permitted; direct edits are prohibited.

---

## 2. Commit Message Standards

All commits must follow standard conventional commit prefixes prefixed with the lane tag:

- `[INT] ...` — Integrator setups, multi-lane merges, repo structure
- `[CORE] ...` — Core engine features, contracts, attention math, bug fixes
- `[GUARD] ...` — Guardrail rules, safety layers, de-id features
- `[CLINICAL] ...` — Clinical rule additions, EHR parser updates
- `[STUDIO] ...` — Dashboard UI updates, benchmark visualization

Examples:
- `[INT] repo setup: gitignore, workflow, repo state`
- `[CORE] feat(K-03): span localization via offset mapping`
- `[GUARD] fix(deid): regex optimization for patient SSN masking`

---

## 3. Integration & Merge Protocol

All integration merges are performed **exclusively by the CORE lane (Integrator)**:

1. **Branch Isolation:** Lanes work independently on their `lane/*` branches.
2. **Push to Remote:** Lanes push their own feature branch (`git push -u origin lane/<name>`).
3. **Pull Request / Integrator Merge:** CORE inspects diffs, runs test suites across all lanes (`pytest tests`, `pytest guard/tests`, etc.), and merges into `main` after verifying:
   - Zero path overlaps / cross-lane file edits.
   - All tests passing.
   - Clean, non-conflicting commit graph.
4. **No Direct Pushes to `main`:** `main` is reserved for verified integrator releases.

---

## 4. Safety & Security Guardrails

- **Zero Hardcoded Secrets:** No API keys, passwords, or tokens in source code.
- **Model Weight Exclusion:** Model files (`*.safetensors`, `*.bin`, `*.gguf`, `*.ckpt`) and `hf_cache/` are strictly ignored via `.gitignore`.
- **Synthetic Data Only:** All test cases and clinical EHR records must use synthetic, non-PHI patient data.
- **Forbidden Git Commands:**
  - `git push --force` / `git push -f`
  - `git reset --hard` on shared history
  - `git clean -fd`
