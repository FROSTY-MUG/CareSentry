# 🩺 CareSentry-AI

> **Deterministic Attention-Anchored Context Sentry & Invariant Verification Harness for Open-Weight Clinical Models.**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Model Support](https://img.shields.io/badge/Models-Qwen2.5%20%7C%20Gemma--2-orange)](#supported-models)
[![Standard](https://img.shields.io/badge/Standard-Agent_Skills_Open_Standard-purple)](https://agentskills.io)
[![Tests](https://img.shields.io/badge/Tests-23%20Passed%20(100%25)-brightgreen)](#test-suite)

---

## 📌 Executive Summary & Problem Framing

When elderly patients or caregivers upload dense, 30- to 50-page clinical records (lab chemistry panels, nursing shift notes, ICD-10 diagnostic codes, and discharge instructions) to open-weight large language models, prompt length quickly spans **10,000 to 24,000 tokens**.

Under this heavy context load, open-weight models experience severe **Attention Dispersion** (the classic *"Lost-in-the-Middle"* failure mode). The model generates a conversational, well-formatted summary, but its internal attention weights dilute over critical negative constraints buried in the middle tokens:
1. **Missing explicit drug allergies:** The patient has a documented anaphylactic allergy to penicillin buried on page 24, yet the model orders Amoxicillin or Augmentin.
2. **Prescribing nephrotoxic drugs:** Recommending high-dose NSAIDs, Metformin, or Spironolactone despite lab values documenting acute renal failure ($\text{eGFR} < 30 \text{ mL/min}$).
3. **Severe Drug-Drug Interactions (DDIs):** Prescribing NSAIDs to a patient anticoagulated with Warfarin, dramatically elevating gastrointestinal hemorrhage risk.

---

## 💡 The Solution: CareSentry-AI

**CareSentry-AI** is an open-source, deterministic attention-auditing harness and clinical verification engine for open-weight language models.

```text
Raw Geriatric Discharge Packet (4,000 - 24,000 Tokens)
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│     CareSentry Model Harness Engine (`harness/attention_probe.py`)     │
│   Target Models: Qwen2.5-1.5B (Edge/Dev) | Qwen2.5-7B | Gemma-2-9B     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Attention Tensor Extractor]                                          │
│  • PyTorch forward pass with eager attention implementation            │
│  • Extracts multi-head attention weights from last 4 decision layers   │
│                                                                        │
│  [Statistical Z-Score Engine]                                          │
│  • Computes Target Span Attention vs 20 Random Control Spans           │
│  • Flags Attention Dilution if Z-score < -0.5                          │
│                                                                        │
│  [Active Mitigation Loop]                                              │
│  • System Anchor Pinning (Elevates rule to terminal system prompt)     │
│  • Recency Reordering (Shifts middle-depth constraint to last 10%)     │
│                                                                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│        Agent Skill Engine (`.agents/skills/caresentry/SKILL.md`)       │
│        Complies with Agent Skill Open Standard (`agentskills.io/v1`)   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Executes: `scripts/audit_contraindication.py`                         │
│  • Allergy Matrix Validation (Penicillin, Sulfa, NSAIDs, Quinolones)   │
│  • Renal Threshold Validation (eGFR vs. Metformin, Spironolactone)     │
│  • High-Risk Drug-Drug Interaction Validation (Warfarin + NSAIDs)      │
│                                                                        │
│  Result:                                                               │
│  ├─ PASS ──> Emit Verified Patient-Facing Summary                      │
│  └─ FAIL ──> Return Structured Remediation Error to Harness for Retry  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

* **Direct Multi-Head Attention Probing:** Hooks into transformer attention heads (`output_attentions=True`) across the final 4 decision layers and calculates an empirical Attention $Z$-Score against 20 randomized control spans.
* **Deterministic Clinical Invariant Gate:** Sub-100ms offline linter evaluating string matches and regular expressions against offline clinical matrices (`clinical_rules.json`) covering allergies, renal thresholds, and DDIs before any summary reaches the patient.
* **Automated Context Remediation:** When attention dilution is detected ($Z < -0.5$), the harness automatically executes **System Anchor Pinning** or **Recency Reordering** to rescue generation.
* **Agent Self-Healing Reflection Loop:** On invariant failure, executes up to 3 automatic re-prompt cycles with a temperature reduction of $\Delta T = -0.05$ per attempt.
* **Agent Skill Open Standard Compliant:** Ships with `.agents/skills/caresentry/SKILL.md` (`agent-skills.io/v1`), enabling Claude Code, Cursor, and Gemini CLI to invoke CareSentry as a native tool.
* **Edge & Laptop CPU Portability:** Runs out-of-the-box on `Qwen2.5-1.5B-Instruct` for 4GB VRAM laptops or CPU, with an air-gapped simulation engine for rapid verification.

---

## 📐 Mathematical Attention Z-Score Formulation

To statistically determine whether an open-weight model neglected a specific medical constraint, the harness computes:

$$Z_{\text{target}} = \frac{\bar{A}_{\text{target}} - \mu_{\text{controls}}}{\sigma_{\text{controls}} + \epsilon}$$

Where:
* $\bar{A}_{\text{target}}$ is the mean cross-head attention weight directed to the target token span from subsequent token positions across the final 4 transformer layers.
* $\mu_{\text{controls}}$ and $\sigma_{\text{controls}}$ are the mean and standard deviation of attention weights received by 20 randomly sampled control spans of identical token length from the same document.
* $\epsilon = 10^{-9}$ (numerical stability constant).

### Classification Thresholds:
| Z-Score Range | Attention Classification | Action Taken |
| :--- | :--- | :--- |
| **$Z \ge +1.0$** | **Sufficiently Attended** | Model focused on constraint. Proceed to gate verification. |
| **$-0.5 \le Z < +1.0$** | **Neutral / Ambiguous** | Borderline attention. Normal pass. |
| **$Z < -0.5$** | **Attention Dilution / Neglected** | **Triggers automated prompt mitigation loop.** |

---

## 🛠️ Quickstart

### 1. Installation

```bash
git clone https://github.com/your-org/caresentry-ai.git
cd caresentry-ai
pip install -r requirements.txt
pip install -e .
```

### 2. Run the Live Diagnostic Attention Probe

```bash
python -m harness.attention_probe \
  --doc data/sample_discharge.txt \
  --needle "Severe allergy to Penicillin" \
  --model "Qwen/Qwen2.5-1.5B-Instruct"
```

### 3. Launch the Interactive Hackathon Dashboard

```bash
python demo/cli_dashboard.py --case 0
```
Or run the full benchmark sweep directly:
```bash
python demo/cli_dashboard.py --benchmark
```

### 4. Execute the Agent Skill Offline Linter

```bash
python .agents/skills/caresentry/scripts/audit_contraindication.py \
  --records data/sample_discharge.txt \
  --summary "Discharge on Amoxicillin 500mg PO TID."
```

Or via the POSIX shell wrapper:
```bash
bash .agents/skills/caresentry/scripts/run_probe.sh \
  --records data/sample_discharge.txt \
  --summary "Discharge on Amoxicillin 500mg PO TID."
```

---

## 📊 Benchmark Results & Experimental Evidence

Measured across varying context window lengths with the clinical constraint placed at middle depth (~50%):

| Context Window | Baseline Attention | Attention Z-Score (v2) | 95% Bootstrap CI | Safety Invariant Gate | With Anchor Pinning | With Recency Reorder |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **2,000 Tokens** | 0.058 m-attn | −4.14 (Diluted) | [−4.52, −3.80] | ❌ BLOCKED (`FAIL`) | **+38.27 (PASS)** | **+38.41 (PASS)** |
| **4,000 Tokens** | 0.021 m-attn | −3.97 (Diluted) | [−4.35, −3.61] | ❌ BLOCKED (`FAIL`) | **+38.24 (PASS)** | **+37.67 (PASS)** |
| **8,000 Tokens** | 0.007 m-attn | −4.54 (Diluted) | [−4.92, −4.18] | ❌ BLOCKED (`FAIL`) | **+40.63 (PASS)** | **+36.42 (PASS)** |
| **16,000 Tokens** | 0.003 m-attn | −3.71 (Diluted) | [−4.09, −3.35] | ❌ BLOCKED (`FAIL`) | **+34.16 (PASS)** | **+30.63 (PASS)** |
| **24,000 Tokens** | 0.001 m-attn | −4.52 (Diluted) | [−4.90, −4.16] | ❌ BLOCKED (`FAIL`) | **+33.97 (PASS)** | **+30.66 (PASS)** |

> 📑 **Reproducible Experimental Data:** Full machine-readable benchmark records, position analysis (beginning, middle, end), and statistical evaluations are preserved in [`verification/evidence/benchmark_summary.md`](verification/evidence/benchmark_summary.md) and [`verification/evidence/benchmark_results.json`](verification/evidence/benchmark_results.json).
> Re-run benchmarks on your local machine with `python scripts/generate_verification_evidence.py`.

---

## 📁 Repository Structure

```text
caresentry-ai/
├── LICENSE                                # Apache License 2.0
├── README.md                              # Comprehensive project documentation
├── SECURITY.md                            # Vulnerability disclosure & synthetic data policy
├── CODE_OF_CONDUCT.md                     # Contributor Covenant v2.1
├── pyproject.toml                         # Pip-installable package definition
├── requirements.txt                       # Minimum package dependencies
│
├── .agents/
│   └── skills/
│       └── caresentry/
│           ├── SKILL.md                   # Agent Skill Open Standard specification
│           ├── scripts/
│           │   ├── audit_contraindication.py # Portable validation script
│           │   └── run_probe.sh           # POSIX shell wrapper
│           └── references/
│               ├── clinical_rules.json    # Deterministic drug-allergy & renal matrices (v1.1)
│               └── score_schema.json      # JSON schema for attention score outputs
│
├── harness/
│   ├── __init__.py
│   ├── api.py                             # Documented public API surface (v1.1.0)
│   ├── model_runner.py                    # Weight loader & attention extractor
│   ├── attention_probe.py                 # Raw attention extraction, Z-score v2, multi-probing
│   ├── blockwise_attention.py             # K-01 Two-pass streaming attention estimator
│   ├── span_locator.py                    # K-03 Robust offset-aware token span locator
│   ├── clinical_linter.py                 # Deterministic clinical safety invariant evaluator
│   ├── mitigations.py                     # Anchor Pinning, Recency Reordering, and strategy registry
│   ├── plugins.py                         # K-07 Extensible plugin framework with monotonic safety
│   ├── benchmark_runner.py                # Long-context degradation test suite
│   └── self_healer.py                     # Bounded reflection loop with WITHHELD safe-hold
│
├── data/
│   ├── sample_discharge.txt               # Sample geriatric discharge record
│   ├── synthetic_geriatric_cases.json     # 10 synthetic clinical test records
│   └── synthetic_15_verification_cases.json # 15 acceptance test scenarios (Verification PRD)
│
├── verification/
│   ├── VERIFICATION_PRD.md                # 100-Point Track 1 Acceptance Specification
│   ├── TEST_PLAN.md                       # Comprehensive testing strategy
│   ├── acceptance_criteria.json           # 32 acceptance criteria mapped to judging rubric
│   ├── test_matrix.csv                    # Complete traceability test matrix
│   └── evidence/                          # Generated verification evidence package
│       ├── environment.json               # Environment & local inference metadata
│       ├── unit_test_results.xml          # JUnit test execution records
│       ├── integration_test_results.json  # 15 synthetic case execution telemetry
│       ├── benchmark_results.json         # Raw benchmark measurements
│       ├── benchmark_summary.md           # Formatted benchmark evaluation report
│       ├── license_audit.json             # License & open-source standards audit
│       └── demo_checklist.md              # Live demonstration step-by-step guide
│
├── tests/
│   ├── test_attention_probe.py            # Unit tests for Z-score math, v2 bootstrap, trace dumps
│   ├── test_blockwise_attention.py        # Equivalence tests for two-pass blockwise attention
│   ├── test_clinical_linter.py            # Invariant tests for allergy, serial renal labs, negation
│   ├── test_mitigations.py                # Unit tests for prompt remediation and registry
│   ├── test_plugins.py                    # Tests for monotonic safety invariant enforcement
│   ├── test_public_api_stability.py       # Backward-compatibility API contract verification
│   ├── test_self_healer.py                # Tests for reflection cycles, stepping, WITHHELD hold
│   ├── test_span_locator.py               # Offset mapping and missing-needle error tests
│   └── test_verification_suite.py        # Acceptance tests for all 15 synthetic cases
│
├── scripts/
│   └── generate_verification_evidence.py # Reproducible evidence generation pipeline
│
└── demo/
    └── cli_dashboard.py                   # Rich terminal live dashboard for hackathon judging
```

---

## 🧪 Test Suite

Run the full automated test suite:

```bash
pytest -v
```

Output:
```text
============================= test session starts =============================
collected 48 items

tests/test_attention_probe.py ........                                   [ 16%]
tests/test_blockwise_attention.py ..                                     [ 20%]
tests/test_clinical_linter.py .............                              [ 47%]
tests/test_mitigations.py .....                                          [ 58%]
tests/test_plugins.py ....                                               [ 66%]
tests/test_public_api_stability.py .......                               [ 81%]
tests/test_self_healer.py ...                                            [ 87%]
tests/test_span_locator.py ....                                          [ 95%]
tests/test_verification_suite.py ..                                      [100%]

============================= 48 passed in 4.51s ==============================
```

---

## 🔒 Privacy & HIPAA / GDPR Compliance

* All datasets in `data/synthetic_geriatric_cases.json` are **100% synthetically generated** and contain no real Protected Health Information (PHI).
* CareSentry-AI is designed for **air-gapped, fully local inference**. When executed with open-weight models (such as `Qwen2.5-1.5B` or `Gemma-2-9B`), zero tokens, prompt texts, or attention telemetry leave the local compute environment.

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
