# 🩺 CareSentry-AI

> **Deterministic Attention-Anchored Context Sentry, Clinical Invariant Verification, and Defense Guard for Open-Weight Medical Models.**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Model Support](https://img.shields.io/badge/Models-Qwen2.5%20%7C%20Gemma--2-orange.svg)](#supported-models)
[![Standard](https://img.shields.io/badge/Standard-Agent_Skills_Open_Standard-purple.svg)](https://agentskills.io)
[![Tests](https://img.shields.io/badge/Tests-130%20Passed%20(100%25)-brightgreen.svg)](#-test-suite)
[![Authors](https://img.shields.io/badge/Authors-Aryan%20Arora%20%7C%20Saksham%20Chawla%20%7C%20Chinmay-darkblue.svg)](AUTHORS.md)

---

## 👥 Authors

CareSentry-AI was developed by:
* **[Aryan Arora](AUTHORS.md)**
* **[Saksham Chawla](AUTHORS.md)**
* **[Chinmay](AUTHORS.md)**

See [AUTHORS.md](AUTHORS.md) for full project attribution and contribution details.

---

## 📌 Executive Summary & Problem Framing

When elderly patients, clinicians, or caregivers input dense, 30- to 50-page clinical records (lab chemistry panels, nursing shift notes, ICD-10 diagnostic codes, and discharge orders) into open-weight large language models, prompt length quickly spans **4,000 to 24,000 tokens**.

Under this heavy context load, open-weight models experience severe **Attention Dispersion** (the classic *"Lost-in-the-Middle"* failure mode). The model generates a conversational, fluent summary, but its internal attention weights dilute over critical negative constraints buried in the middle tokens:
1. **Missing explicit drug allergies:** The patient has a documented anaphylactic allergy to penicillin buried on page 24, yet the model orders Amoxicillin or Augmentin.
2. **Prescribing nephrotoxic drugs:** Recommending high-dose NSAIDs, Metformin, or Spironolactone despite lab values documenting acute renal failure ($\text{eGFR} < 30 \text{ mL/min}$).
3. **Severe Drug-Drug Interactions (DDIs):** Prescribing NSAIDs to a patient anticoagulated with Warfarin, dramatically elevating gastrointestinal hemorrhage risk.
4. **Adversarial Injections & Hallucinations:** Malicious prompt injections within EHR text or phantom medication claims without evidence grounding.

---

## 💡 The Unified Solution: CareSentry Ecosystem

CareSentry-AI provides a tri-layer, deterministic safety harness for open-weight medical models:

```text
                     Raw Geriatric Discharge Packet (4,000 - 24,000 Tokens)
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. PRE-FLIGHT & INFERENCE DEFENSE LAYER (Track C: CareSentry Guard)                         │
│ • Prompt-Injection Scanner: Neutralizes delimiter spoofing & zero-width steganography       │
│ • Constrained Decoding: Prefix Trie LogitsProcessor blocks contraindicated tokens           │
│ • Intermediate Linear Probes & Attention Steering across transformer layers                │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. CORE ATTENTION PROBING & MITIGATION ENGINE (Track A: Core Harness)                       │
│ • PyTorch Forward Hooks: Multi-head attention extraction across terminal decision layers    │
│ • Statistical Z-Score v2: Depth-stratified controls with bootstrap 95% confidence intervals │
│ • Active Mitigation Loop: System Anchor Pinning & Recency Reordering                        │
│ • Reflection Self-Healer: Bounded re-prompting with temperature stepping                    │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. EXTENDED CLINICAL INVARIANT & OMISSION GATE (Track B: CareSentry-AI Plus)                │
│ • RxNorm Lite & WHO-ATC Lexicon: Normalizes 180+ drug aliases and brand names               │
│ • Invariant Rule Packs: Cross-reactivity, AGS Beers Criteria 2023, DDI, Cockcroft-Gault CrCl │
│ • Reverse-Omission Sentry: Verifies all raw EHR negative constraints appear in summary       │
│ • Cryptographic Tamper-Evident Audit Trail & Interactive SVG Attention Heatmaps             │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. INTEGRATION & PRESENTATION SURFACES                                                      │
│ ├─ Gradio Web UI (`http://127.0.0.1:7860`): Clinician portal & interactive heatmap viewer   │
│ ├─ Guard UI Console (`http://127.0.0.1:8000`): Policy dashboard & audit telemetry         │
│ ├─ OpenAI Safety Gateway (`http://127.0.0.1:8787`): `/v1/chat/completions` drop-in proxy    │
│ ├─ Model Context Protocol (MCP): Claude Desktop / Agent native tools                        │
│ └─ Agent Skills: 3 Open-Standard Skills (`agent-skills.io/v1`)                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Capabilities by Track

### Track A: Core Attention Harness (`harness/`)
* **Direct Multi-Head Attention Probing:** Hooks into transformer attention heads (`output_attentions=True`) across final decision layers.
* **Blockwise Memory-Bounded Estimator (K-01):** Evaluates attention weights with $O(S \cdot K)$ memory instead of $O(S^2)$, eliminating OOM errors at 24,000 tokens on 16GB RAM.
* **Statistical Z-Score Engine (K-02):** Evaluates needle attention against depth-stratified control spans with bootstrap 95% confidence intervals $[Z_{low}, Z_{high}]$.
* **Automated Context Remediation:** Anchor Pinning and Recency Reordering rescue diluted attention ($Z < -0.5$).
* **Deterministic Baseline Linter:** Offline regex and exact substring matching against `clinical_rules.json`.

### Track B: CareSentry-AI Plus (`plus/`)
* **Extended Invariant Rule Packs (`plus/rule_packs/`):**
  - **Cross-Reactivity:** Penicillin $\to$ 1st-generation cephalosporins, sulfonamides, aspirin/AERD.
  - **Dose-Aware Renal Function:** Computes Cockcroft-Gault Creatinine Clearance (CrCl) and CKD-EPI 2021 eGFR from labs. Enforces cutoffs for Metformin, Spironolactone, NSAIDs, and DOACs.
  - **Beers Criteria 2023:** Flags high-risk geriatric anticholinergics and sedatives.
  - **Drug-Drug Interactions (DDIs):** Warfarin + NSAIDs, Clopidogrel + Omeprazole, duplicate NSAID therapies.
* **Reverse Omission Sentry:** Analyzes source records to ensure negative constraints, active allergies, and baseline renal warnings are retained in the discharge instructions.
* **Tamper-Evident Cryptographic Audit Trail:** SHA-256 chained ledger recording all evaluations, telemetry, and verdicts.
* **Clinician Attention Heatmap:** Interactive, standalone SVG heatmaps with per-token attention intensity.
* **Gradio Web UI (`plus/webui/app.py`):** Live web UI serving port `7860`.
* **Model Context Protocol (MCP) Server:** Native MCP tools for external AI agents.

### Track C: CareSentry Guard (`guard/`)
* **Clinical Prompt-Injection Scanner:** Rejection of jailbreaks, roleplay inversions, delimiter spoofing, and zero-width steganography without false-flagging legitimate medical directives.
* **Constrained Decoding:** Invariant-guided prefix trie logits processor constraining output generation tokens at runtime.
* **Evidence Grounding Engine:** Sentence-level attribution verifying that clinical claims trace back to documented facts.
* **OpenAI-Compatible Safety Gateway (`127.0.0.1:8787`):** Instant drop-in safety proxy for any OpenAI-compatible application.
* **Guard UI Console (`guard/ui/`):** Dedicated web interface for policy inspection and safety audits.

---

## 📐 Mathematical Formulation

### Attention $Z$-Score

To statistically verify whether a medical constraint was attended to by the model, the harness computes:

$$Z_{\text{target}} = \frac{\bar{A}_{\text{target}} - \mu_{\text{controls}}}{\sigma_{\text{controls}} + \epsilon}$$

Where:
* $\bar{A}_{\text{target}}$ is the mean cross-head attention weight directed to the target token span from subsequent token positions across the final 4 transformer layers.
* $\mu_{\text{controls}}$ and $\sigma_{\text{controls}}$ are the mean and standard deviation of attention weights received by 20 depth-stratified control spans of identical length.
* $\epsilon = 10^{-9}$ (numerical stability constant).

### Classification Thresholds:
| $Z$-Score Range | Attention Classification | Active Remediation |
| :--- | :--- | :--- |
| **$Z \ge +1.0$** | **Sufficiently Attended** | Constraint well-attended. Proceed to invariant gate. |
| **$-0.5 \le Z < +1.0$** | **Neutral / Ambiguous** | Borderline attention. Standard gate verification. |
| **$Z < -0.5$** | **Attention Dilution / Neglected** | **Triggers Automated Mitigation Loop (Anchor Pinning / Reordering).** |

---

## 🛠️ Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/FROSTY-MUG/CareSentry.git
cd CareSentry

# Install Core dependencies
pip install -r requirements.txt
pip install -e .

# Install Plus & Guard extensions
pip install -e ./plus
pip install -e ./guard
```

### 2. Launching the Web Interfaces

#### Option A: CareSentry-AI Plus Web UI (Gradio)
```bash
python plus/webui/app.py
# Opens at http://127.0.0.1:7860
```

#### Option B: CareSentry Guard Console
```bash
python guard/src/caresentry_guard/demo/web_dashboard.py
# Opens at http://127.0.0.1:8000
```

#### Option C: OpenAI Safety Gateway
```bash
python -m caresentry_guard.cli serve --port 8787
# Proxies requests to http://127.0.0.1:8787/v1/chat/completions
```

### 3. Running Diagnostic Probes via CLI

```bash
# Core Attention Probe
python -m harness.attention_probe \
  --doc data/sample_discharge.txt \
  --needle "Severe allergy to Penicillin" \
  --model "Qwen/Qwen2.5-1.5B-Instruct"

# CareSentry-AI Plus Extended Audit
python -m caresentry_plus.cli audit \
  --records data/sample_discharge.txt \
  --summary "Discharge orders: Continue Metformin 1000mg BID."

# CareSentry Guard Complete Audit
python -m caresentry_guard.cli audit \
  --records data/sample_discharge.txt \
  --summary "Discharge orders: Take Amoxicillin 500mg PO TID."
```

### 4. Running as Native Agent Skills

CareSentry ships with 3 specifications conforming to the **Agent Skill Open Standard** (`agent-skills.io/v1`):
* [`.agents/skills/caresentry/SKILL.md`](.agents/skills/caresentry/SKILL.md): Core attention probe & invariant linter
* [`.agents/skills/caresentry-plus/SKILL.md`](.agents/skills/caresentry-plus/SKILL.md): Extended rule packs, omission sentry, and SVG heatmaps
* [`.agents/skills/caresentry-guard/SKILL.md`](.agents/skills/caresentry-guard/SKILL.md): Injection defense, constrained decoding, and patient packs

---

## 🧪 Test Suite

The unified repository maintains **130 tests with 100% pass rate** across all tracks:

```bash
# Run entire repository test suite
pytest tests plus/tests guard/tests -v
```

### Breakdown:

| Test Suite | Path | Tests Passed | Status |
| :--- | :--- | :---: | :---: |
| **Track A (Core Harness)** | `tests/` | 46 / 46 | ✅ 100% PASS |
| **Track B (CareSentry-AI Plus)** | `plus/tests/` | 53 / 53 | ✅ 100% PASS |
| **Track C (CareSentry Guard)** | `guard/tests/` | 31 / 31 | ✅ 100% PASS |
| **Total Unified Suite** | | **130 / 130** | ✅ **100% PASS** |

---

## 📊 Benchmark Telemetry

### Context Degradation & Mitigation (Track A)
Evaluated across varying context window lengths with the clinical needle placed at middle depth (~52%):

| Context Window | Baseline Attention | Attention Z-Score | Invariant Gate Status | With Anchor Pinning | With Recency Reorder |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **2,000 Tokens** | 0.058 m-attn | −4.14 (Diluted) | ❌ FAIL (Constraint Missed) | **+38.27 (PASS)** | **+38.41 (PASS)** |
| **4,000 Tokens** | 0.021 m-attn | −3.97 (Diluted) | ❌ FAIL (Constraint Missed) | **+38.24 (PASS)** | **+37.67 (PASS)** |
| **8,000 Tokens** | 0.007 m-attn | −4.54 (Diluted) | ❌ FAIL (Constraint Missed) | **+40.63 (PASS)** | **+36.42 (PASS)** |
| **16,000 Tokens** | 0.003 m-attn | −3.71 (Diluted) | ❌ FAIL (Constraint Missed) | **+34.16 (PASS)** | **+30.63 (PASS)** |
| **24,000 Tokens** | 0.001 m-attn | −4.52 (Diluted) | ❌ FAIL (Constraint Missed) | **+33.97 (PASS)** | **+30.66 (PASS)** |

### Defense & Evaluation Benchmarks (Track C)

| Component | Metric | Value | Baseline / Notes |
| :--- | :--- | :---: | :--- |
| **Prompt Injection Scanner** | Precision | **100.0%** | Zero false positives on 85 benign medical orders |
| **Prompt Injection Scanner** | Recall | **97.6%** | Evaluated on 85 adversarial jailbreak variants |
| **Evidence Grounding** | Precision | **100.0%** | Catches 100% of fabricated drug orders |
| **Evidence Grounding** | Safety Recall | **98.0%** | Evaluated on 105 labeled clinical sentences |
| **105-Case Long-Context Bench**| Mitigation Rescue | **100.0%** | Rescues 100% of middle-depth lost constraints |
| **105-Case Long-Context Bench**| Audit Latency | **2.47 ms** | Sub-3ms offline evaluation latency on CPU |

---

## 🔒 Privacy & HIPAA / GDPR Compliance

* **Synthetic Data Only:** All clinical test cases (`data/synthetic_geriatric_cases.json`, `guard/data_guard/synthetic_cases_100.json`) are **100% synthetically generated** and contain zero real Protected Health Information (PHI).
* **Air-Gapped & Offline Inference:** CareSentry-AI is engineered for completely local, air-gapped execution. Zero tokens, raw clinical text, or attention tensors leave the local compute environment.

---

## 📄 License & Attribution

Licensed under the [Apache License 2.0](LICENSE).  
Authored by **Aryan Arora**, **Saksham Chawla**, and **Chinmay**. See [AUTHORS.md](AUTHORS.md) for full details.
