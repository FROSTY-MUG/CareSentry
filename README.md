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

## 📊 Benchmark Results

Evaluated across varying context window lengths with the clinical needle placed at middle depth (~52%):

| Context Window | Baseline Attention | Attention Z-Score | Invariant Gate Status | With Anchor Pinning | With Recency Reorder |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **2,000 Tokens** | 0.058 m-attn | −4.14 (Diluted) | ❌ FAIL (Constraint Missed) | **+38.27 (PASS)** | **+38.41 (PASS)** |
| **4,000 Tokens** | 0.021 m-attn | −3.97 (Diluted) | ❌ FAIL (Constraint Missed) | **+38.24 (PASS)** | **+37.67 (PASS)** |
| **8,000 Tokens** | 0.007 m-attn | −4.54 (Diluted) | ❌ FAIL (Constraint Missed) | **+40.63 (PASS)** | **+36.42 (PASS)** |
| **16,000 Tokens** | 0.003 m-attn | −3.71 (Diluted) | ❌ FAIL (Constraint Missed) | **+34.16 (PASS)** | **+30.63 (PASS)** |
| **24,000 Tokens** | 0.001 m-attn | −4.52 (Diluted) | ❌ FAIL (Constraint Missed) | **+33.97 (PASS)** | **+30.66 (PASS)** |

Telemetry exported to `benchmark_results.json`.

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
├── benchmark_results.json                 # Exported context degradation telemetry
│
├── .agents/
│   └── skills/
│       └── caresentry/
│           ├── SKILL.md                   # Agent Skill Open Standard specification
│           ├── scripts/
│           │   ├── audit_contraindication.py # Portable validation script
│           │   └── run_probe.sh           # POSIX shell wrapper
│           └── references/
│               ├── clinical_rules.json    # Deterministic drug-allergy & renal matrices
│               └── score_schema.json      # JSON schema for attention score outputs
│
├── harness/
│   ├── __init__.py
│   ├── model_runner.py                    # Weight loader & attention extractor
│   ├── attention_probe.py                 # Raw attention extraction and Z-score engine
│   ├── clinical_linter.py                 # Deterministic clinical safety invariant evaluator
│   ├── mitigations.py                     # Anchor Pinning and Recency Reordering logic
│   ├── benchmark_runner.py                # Needle-in-haystack degradation test (2k to 24k)
│   └── self_healer.py                     # Reflection retry loop on invariant failure
│
├── data/
│   ├── sample_discharge.txt               # Sample geriatric discharge record
│   └── synthetic_geriatric_cases.json     # 10 synthetic clinical test records (HIPAA safe)
│
├── tests/
│   ├── __init__.py
│   ├── test_attention_probe.py            # Unit tests for Z-score math and tensor hooks
│   ├── test_clinical_linter.py            # Unit tests for allergy and renal failure checks
│   ├── test_mitigations.py                # Unit tests for prompt remediation
│   └── test_self_healer.py                # Unit tests for reflection self-healing loop
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
collected 23 items

tests/test_attention_probe.py::test_needle_span_location PASSED          [  4%]
tests/test_attention_probe.py::test_control_spans_sampling PASSED        [  8%]
tests/test_attention_probe.py::test_z_score_mathematical_precision PASSED [ 13%]
tests/test_attention_probe.py::test_probe_execution_and_schema_compliance PASSED [ 17%]
tests/test_attention_probe.py::test_classification_thresholds PASSED     [ 21%]
tests/test_clinical_linter.py::test_penicillin_allergy_catches_amoxicillin PASSED [ 26%]
tests/test_clinical_linter.py::test_penicillin_allergy_allows_safe_macrolide PASSED [ 30%]
tests/test_clinical_linter.py::test_cephalosporin_cross_reactivity_detected PASSED [ 34%]
tests/test_clinical_linter.py::test_sulfa_allergy_catches_bactrim PASSED [ 39%]
tests/test_clinical_linter.py::test_renal_egfr_under_30_catches_metformin PASSED [ 43%]
tests/test_clinical_linter.py::test_renal_egfr_under_30_catches_spironolactone PASSED [ 47%]
tests/test_clinical_linter.py::test_renal_normal_egfr_cleared PASSED     [ 52%]
tests/test_clinical_linter.py::test_drug_drug_interaction_warfarin_and_nsaid PASSED [ 56%]
tests/test_clinical_linter.py::test_execution_latency_sub_100ms PASSED   [ 60%]
tests/test_clinical_linter.py::test_all_10_synthetic_geriatric_cases PASSED [ 65%]
tests/test_mitigations.py::test_anchor_pinning_formatting PASSED         [ 69%]
tests/test_mitigations.py::test_anchor_pinning_with_custom_system_prompt PASSED [ 73%]
tests/test_mitigations.py::test_recency_reordering PASSED                [ 78%]
tests/test_mitigations.py::test_combined_remediation PASSED              [ 82%]
tests/test_mitigations.py::test_mitigation_remedies_attention_dilution PASSED [ 86%]
tests/test_self_healer.py::test_clean_summary_passes_without_healing PASSED [ 91%]
tests/test_self_healer.py::test_unsafe_summary_heals_via_reflection PASSED [ 95%]
tests/test_self_healer.py::test_reflection_temperature_stepping_and_max_cycles PASSED [100%]

============================= 23 passed in 3.88s ==============================
```

---

## 🔒 Privacy & HIPAA / GDPR Compliance

* All datasets in `data/synthetic_geriatric_cases.json` are **100% synthetically generated** and contain no real Protected Health Information (PHI).
* CareSentry-AI is designed for **air-gapped, fully local inference**. When executed with open-weight models (such as `Qwen2.5-1.5B` or `Gemma-2-9B`), zero tokens, prompt texts, or attention telemetry leave the local compute environment.

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).
