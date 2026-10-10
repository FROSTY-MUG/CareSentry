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