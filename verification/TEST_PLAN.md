# CareSentry-AI Engineering Test Plan

**Document ID:** CS-TP-001  
**Project Slug:** `caresentry-ai`  
**Version:** 1.0.0  
**Target Release:** Hacktoberfest Hack Day (Track 1 — Open-Source AI Project)  
**Standard Compliance:** agent-skills.io/v1  

---

## 1. Testing Architecture & Strategy

CareSentry-AI verification is organized into four complementary layers:

```text
┌────────────────────────────────────────────────────────────┐
│ Layer 4: Repository, Standards & Compliance Auditing      │
│ (License, Security, Agent Skill, Supply-Chain & Manifests) │
├────────────────────────────────────────────────────────────┤
│ Layer 3: End-to-End Execution & Demonstration Runs         │
│ (Live CLI Dashboard, Benchmark Sweeps, Agent Skill Shell)  │
├────────────────────────────────────────────────────────────┤
│ Layer 2: Subsystem Integration Testing                     │
│ (Probe + Model, Linter + Reflection, Multi-Constraint)     │
├────────────────────────────────────────────────────────────┤
│ Layer 1: Deterministic Unit Testing                        │
│ (Z-Score Math, Control Sampling, String Matching, Retries) │
└────────────────────────────────────────────────────────────┘
```

---

## 2. Test Suites & Objectives

### Category 1: Open-Source AI & Model Integration (30 Points)
- **AI-01 (Model Loading):** Test tokenizer and model initialization for `Qwen2.5-1.5B-Instruct` with `output_attentions=True` and `attn_implementation="eager"`.
- **AI-02 (Local Inference):** Verify local model forward execution without external API dependencies.
- **AI-03 (Attention Extraction):** Assert that extracted attention tensors have shape `[batch, heads, seq_len, seq_len]` across the final 4 decision layers.
- **AI-04 (Statistical Z-Score):** Verify formula $Z = \frac{\bar{A}_{\text{target}} - \mu}{\sigma + 10^{-9}}$ against deterministic mathematical references.
- **AI-05 (Randomized Control Sampling):** Assert $N=20$ non-overlapping control spans of identical token length.
- **AI-06 (Quantization Support):** Support FP16 and 4-bit NormalFloat (NF4 via `bitsandbytes`).
- **AI-07 (Model Portability):** Support Qwen2.5-1.5B, Qwen2.5-7B, and Gemma-2-9B architectures.

### Category 2: Live Working Demo & Functionality (25 Points)
- **DEMO-01 (Clean Installation):** Clean environment setup from `requirements.txt` and `pyproject.toml`.
- **DEMO-02 (Synthetic PASS Case):** Verified clinical pass for non-conflicting patient record.
- **DEMO-03 (Allergy Detection):** Verified intercept of Penicillin, Sulfa, NSAID contraindications.
- **DEMO-04 (Renal Invariant):** Verified intercept of Metformin/Spironolactone when eGFR < 30 mL/min.
- **DEMO-05 (Attention Classification):** Boundary tests at $Z = -0.5$ and $Z = +1.0$.
- **DEMO-06 (Mitigation Execution):** Verification of System Anchor Pinning and Recency Reordering.
- **DEMO-07 (Bounded Reflection):** Max 3 cycles with $\Delta T = -0.05$ temperature stepping; safe termination on exhaustion (`WITHHELD`).
- **DEMO-08 (Dashboard Visibility):** Terminal rich dashboard with live telemetry panels.

### Category 3: Innovation & Real Problem Utility (20 Points)
- **INN-01 (Long-Context Benchmarks):** Degradation curves from 2,000 to 24,000 tokens.
- **INN-02 (Constraint Placement):** Sensitivity at beginning (10%), middle (50%), and end (90%).
- **INN-03 (Mitigation Efficacy):** Direct comparison of baseline $Z$ vs post-mitigation $Z$.
- **INN-04 (Safety Gate Independence):** High attention cannot override invariant violations; low attention does not falsely cause clinical violation.
- **INN-05 (Confusion Matrix):** Detection rate, false-positive rate, and mitigation success rate across 15 synthetic cases.
- **INN-06 (Reproducibility):** Fixed seed produces bitwise identical telemetry.

### Category 4: Open Source Standards & OSI License (15 Points)
- **OSS-01 (OSI License):** Apache-2.0 text in repo root, declared in `pyproject.toml`.
- **OSS-02 (Repository Consistency):** No broken links, consistent naming.
- **OSS-03 (Code of Conduct):** Contributor Covenant v2.1.
- **OSS-04 (Security Policy):** Operational security disclosure policy.
- **OSS-05 (Agent Skills):** Strict adherence to `agent-skills.io/v1` under 500 lines.
- **OSS-06 (Automated CI):** Automated pytest execution on GitHub Actions.
- **OSS-07 (Supply-Chain):** Review dependencies, license compatibility, and synthetic data air-gapping.

### Category 5: Documentation & Pitch (10 Points)
- **DOC-01 (Quickstart):** 3-step quickstart in `README.md`.
- **DOC-02 (Architecture Flow):** Full ASCII/Mermaid flow diagrams.
- **DOC-03 (Clinical Disclaimer):** Explicit research-only safety disclosures.
- **DOC-04 (Benchmark Evidence):** Telemetry linked directly to `benchmark_results.json`.
- **DOC-05 (Demo Script):** 2-minute pitch structure and walkthrough.
- **DOC-06 (Integrity Audit):** All paths, files, and links verified.

---

## 3. Test Execution Commands

```bash
# 1. Run all Unit & Integration Tests with JUnit XML output
pytest tests/ -v --junitxml=verification/evidence/unit_test_results.xml

# 2. Run Verification Evidence Generator
python scripts/generate_verification_evidence.py

# 3. Launch Live Dashboard Demo
python demo/cli_dashboard.py --case 0
```
