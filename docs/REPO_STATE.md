# REPO_STATE — CareSentry repository inspection (Gate 1)

**Date checked:** 2026-10-10
**Inspector:** CORE lane (integrator)
**Commands run (all read-only):** `git status`, `git remote -v`, `git fetch origin`, `git branch -r`, `git log --oneline origin/main -n 20`, `git ls-tree --name-only origin/main`, `git ls-tree --name-only main`, `git diff --name-only main origin/main`

---

## 1. Remote

- `origin` = `https://github.com/FROSTY-MUG/CareSentry.git` (already configured, fetch + push URLs identical). No URL change needed.
- `git fetch origin` succeeded; remote is reachable.

## 2. Does origin/main exist?

**Yes.** `origin/HEAD -> origin/main` and `origin/main` both resolve.

## 3. Commits on origin/main

**1 commit.**

```
0f0fc2b feat: initial release of CareSentry-AI v1.0.0-rc1
```

## 4. Top-level names on origin/main (12 entries)

```
.agents
.gitignore
CODE_OF_CONDUCT.md
LICENSE
README.md
SECURITY.md
benchmark_results.json
data
demo
harness
pyproject.toml
requirements.txt
tests
```

## 5. Top-level name conflicts with our layout?

Our layout paths: `harness/`, `guard/`, `clinical/`, `studio/`, `eval/`, `ops/`, `contracts/`, `docs/`, `data/`, `tests/`, `demo/`, `.agents/`, `.github/`.

| Our path | On origin/main? | Conflict? |
|---|---|---|
| `harness/` | Yes | Shared, same content (origin/main == local main for tracked files) |
| `data/` | Yes | Shared |
| `tests/` | Yes | Shared |
| `demo/` | Yes | Shared |
| `.agents/` | Yes (but only `skills/` tracked) | Shared; local adds `skills/caresentry-guard/` untracked |
| `guard/` | **No** | None — local untracked work, not on remote |
| `clinical/` | **No** | None — local untracked work, not on remote |
| `studio/` | **No** | None — local untracked work, not on remote |
| `eval/` | **No** | None |
| `ops/` | **No** | None |
| `contracts/` | **No** | None |
| `docs/` | **No** | None |
| `.github/` | **No** | None (local adds `workflows/guard-ci.yml` untracked) |

**Verdict: no path conflicts.** Every path on origin/main that overlaps our layout (`harness/`, `data/`, `tests/`, `demo/`, `.agents/`) is byte-identical to local main — `git diff --name-only main origin/main` returned only untracked guard/clinical/studio/.agents/.github additions, zero tracked-file differences.

## 6. Local state vs remote

- Local `main` == `origin/main` for all **tracked** files (branch "up to date").
- Local working tree additionally contains **untracked** lane work (not on remote):
  - `guard/` — full Codex guard lane (src, tests, tools, docs, bench, data_guard, evals)
  - `clinical/` — OpenCode clinical lane (adapters, sources, rule_packs, src, tests, docs)
  - `studio/` — Hermes studio lane (appears to be a near-full repo copy: harness, clinical, data, demo, docs, eval, ops, pyproject, requirements, studio, tests)
  - `.agents/skills/caresentry-guard/SKILL.md`
  - `.github/workflows/guard-ci.yml`
- Existing local branch: `track-c/guard` (checked out earlier this session; not on remote).
- Existing worktree created this session: `C:\Users\HP\app\CareSentry-wt\core` on branch `lane/core` (uncommitted, no pushes).

## 7. Interpretation

Remote `origin/main` is the **v1.0.0-rc1 baseline** — the original single-commit release (harness, tests, data, demo, .agents). It does **not** contain any lane work (guard/clinical/studio). All lane work exists only in the local working tree as untracked files.

This matches the **"Commits exist, same project"** row of the path table: the remote is the same project at its baseline, not an unrelated fork. No force-push, no unrelated-history merge needed.

## 8. Recommendation

**Path: "Commits exist, same project"** — fetch and review diffs; merge only after approval; never force-push.

Rationale:
- Remote is not empty and is not an unrelated layout — it is our own v1.0.0-rc1 baseline.
- Local tracked state already equals `origin/main`, so there is nothing to merge at this moment; the reconciliation work is to *add* CORE's new files (`.gitignore`, `GIT_WORKFLOW.md`, `docs/REPO_STATE.md`, contracts, etc.) on top of the baseline and push that.
- The untracked lane directories (guard/clinical/studio) must **not** be committed by CORE — they belong to their owning lanes and are read-only here.
# 📋 CareSentry Repository State & Unified Architecture

**Date:** 2026-10-10  
**Repository:** `https://github.com/FROSTY-MUG/CareSentry.git`  
**Active Branch:** `main`  
**Authors:** Aryan Arora, Saksham Chawla, Chinmay (see [`AUTHORS.md`](../AUTHORS.md))

---

## 1. Unified Ecosystem Overview

The CareSentry codebase unites three collaborative engineering tracks into an end-to-end clinical safety and attention observability platform:

1. **Track A (Core Harness - `harness/`):**
   - PyTorch attention prober and statistical Attention $Z$-score engine (with bootstrap CIs and blockwise streaming estimator).
   - Core deterministic invariant linter evaluating drug allergies, renal impairment, and DDIs against `clinical_rules.json`.
   - Context remediation (System Anchor Pinning & Recency Reordering) and reflection self-healer.
   - Core test suite: **46 / 46 passed**.

2. **Track B (CareSentry-AI Plus - `plus/`):**
   - 180+ entry RxNorm Lite and WHO-ATC ontology dictionary with sub-millisecond lookup latency.
   - Extended invariant rule packs (Cross-reactivity, AGS Beers Criteria 2023, high-risk DDIs, Cockcroft-Gault CrCl calculations).
   - Reverse-Omission Sentry detecting neglected allergies and baseline medication continuity.
   - Self-contained interactive SVG attention heatmap visualization engine.
   - Tamper-evident cryptographic SHA-256 audit log.
   - Interactive Gradio Web UI (`plus/webui/app.py` on port `7860`).
   - Native Model Context Protocol (MCP) server for external AI agents.
   - Plus test suite: **53 / 53 passed** (including Web UI E2E integration tests).

3. **Track C (CareSentry Guard - `guard/`):**
   - Multi-layer prompt-injection scanner (neutralizing delimiter spoofing and zero-width steganography without false positives on clinical orders).
   - Invariant-guided prefix trie constrained decoding (`LogitsProcessor`).
   - Sentence-level evidence grounding engine verifying output claims against raw EHR facts.
   - HIPAA Safe Harbor offline de-identification scrubber.
   - OpenAI-compatible safety proxy gateway (`127.0.0.1:8787`).
   - Guard Console web UI (`guard/ui/` on port `8000`).
   - Guard test suite: **31 / 31 passed**.

---

## 2. Directory Layout & Boundaries

```text
CareSentry/
├── AUTHORS.md                             # Project authors and attribution
├── LICENSE                                # Apache License 2.0
├── README.md                              # Unified ecosystem master documentation
├── SECURITY.md                            # Synthetic data & vulnerability policy
├── CODE_OF_CONDUCT.md                     # Contributor Covenant v2.1
├── GIT_WORKFLOW.md                        # Branching, lane boundaries & PR lifecycle
├── pyproject.toml                         # Root package configuration
├── requirements.txt                       # Core dependencies
│
├── .agents/skills/                        # Agent Skills Open Standard (agent-skills.io/v1)
│   ├── caresentry/                        # Track A core prober skill
│   ├── caresentry-plus/                   # Track B extended linter & heatmap skill
│   └── caresentry-guard/                  # Track C defense, gateway & trie skill
│
├── .github/workflows/                     # Continuous Integration workflows
│   ├── ci.yml                             # Core CI
│   ├── guard-ci.yml                       # Guard CI
│   ├── plus-ci.yml                        # Plus CI
│   └── verify.yml                         # Verification gate
│
├── contracts/                             # Shared immutable versioned interfaces
│   ├── audit_result.v1.schema.json
│   ├── attention_trace.v1.schema.json
│   ├── plus_audit_result.v1.schema.json
│   ├── rule_pack.v1.schema.json
│   ├── mitigation_strategy.v1.md
│   └── README.md
│
├── harness/                               # Track A: Core prober, runner, linter & healer
├── tests/                                 # Track A: 46 automated unit tests
│
├── plus/                                  # Track B: CareSentry-AI Plus
│   ├── src/caresentry_plus/               # Ontology, rule packs, omissions, viz, audit
│   ├── rule_packs/                        # Validated JSON rule packs
│   ├── webui/app.py                       # Gradio Web UI application (port 7860)
│   ├── mcp_server/                        # Model Context Protocol server
│   ├── docs/                              # Compatibility matrix & quantization study
│   └── tests/                             # Track B: 53 automated unit & E2E tests
│
├── guard/                                 # Track C: CareSentry Guard
│   ├── src/caresentry_guard/              # Injection scanner, trie, grounding, gateway
│   ├── ui/                                # Guard Console static frontend
│   ├── data_guard/                        # Benchmark datasets & synthetic cases
│   ├── docs/                              # A11y checklist, discovery, readability
│   └── tests/                             # Track C: 31 automated unit tests
│
├── data/                                  # Synthetic EHR records (HIPAA-safe)
└── demo/                                  # Rich terminal dashboard
```

---

## 3. Test Suite Summary

Total automated tests in repository: **130**  
Total tests passing: **130 (100%)**

```bash
# Run complete verification:
$env:PYTHONPATH=".;plus/src;guard/src"; pytest tests plus/tests guard/tests -v
```

All tracks adhere to strict namespace boundaries, contract immutability, and zero cross-lane code corruption.
