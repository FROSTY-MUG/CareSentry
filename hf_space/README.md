---
title: CareSentry-AI - Clinical Safety Sentry & Attention-Anchoring Gate
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: gradio
sdk_version: 5.20.1
app_file: app.py
pinned: false
license: apache-2.0
short_description: Offline clinical safety verification and attention-anchoring gate for open-weight medical models.
---

# 🛡️ CareSentry-AI: Clinical Safety Sentry & Attention-Anchoring Gate
> **Live Hugging Face Space Deployment** (Optimized for Free 16GB Tier: 2 vCPU · 16 GB RAM)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Model](https://img.shields.io/badge/Model-Qwen2.5--1.5B--Instruct-purple.svg)](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Gradio](https://img.shields.io/badge/SDK-Gradio_5%2B-orange.svg)](https://gradio.app)

---

## 🏥 1. Clinical Safety Crisis: "Lost-in-the-Middle" in Long Contexts
When elderly or complex patients are discharged from hospitals, clinical documentation spans 30 to 50 pages (10,000 to 24,000 tokens) of lab panels, nursing shift notes, allergy histories, and physician orders.

When open-weight foundation models (e.g., `Qwen/Qwen2.5-1.5B-Instruct`, `Gemma-2-2B`, `Llama-3.2`) summarize these records, their internal self-attention dilutes over critical safety constraints buried in the middle tokens:
1. **Dropped Allergies:** The record notes *"Severe anaphylaxis to Penicillin"*, but the model discharges the patient on Amoxicillin.
2. **Renal Dosage Violations:** The lab notes an eGFR of 22 mL/min (CKD Stage 4), but the model re-authorizes Metformin, risking fatal lactic acidosis.
3. **Silent Omission:** The model outputs fluent, polite instructions that fail to warn the patient of life-threatening interactions.

---

## ⚙️ 2. What CareSentry-AI Does
CareSentry-AI is the **offline, deterministic safety verification and attention-anchoring gate** that wraps open-weight medical models with two synchronized layers:

1. **Eager Attention Probing ($Z$-Score):**
   - Probes raw Transformer self-attention tensors in the terminal 4 decision layers ($L_{24}$ to $L_{27}$).
   - Computes statistical cross-head attention $Z$-score against control token spans:
     - **$Z \ge +1.0$:** Sufficiently Attended (Anchored).
     - **$-0.5 \le Z < +1.0$:** Borderline Attention.
     - **$Z < -0.5$:** Attention Diluted (Lost in Middle).
2. **Deterministic Clinical Invariant Gate:**
   - Zero-hallucination regex and AST rule engine that enforces drug contraindications, allergy invariants, and renal dosing rules with 100% precision.
   - Inspects both EHR source inputs and proposed outputs to prevent silent clinical omissions.

---

## 🚀 3. Hugging Face Spaces Deployment Architecture
This Space is built specifically for **Hugging Face Free Tier (2 vCPU · 16 GB RAM)**:
- **Low Memory Footprint:** Loads `Qwen/Qwen2.5-1.5B-Instruct` using `torch.float32` on CPU (or `torch.float16` if GPU is assigned).
- **Eager Attention Extraction:** Configures `attn_implementation="eager"` and `output_attentions=True` to extract multi-head attention tensors directly.
- **Side-by-Side Diagnostic Cards:**
  - **Card 1:** Context Length & Attention Z-Score Diagnostic.
  - **Card 2:** Deterministic Clinical Invariant Gate (PASS/FAIL badge).
  - **Card 3:** Detected Violations Log.
  - **Card 4:** Generated Patient Summary (withheld / annotated if unsafe).
- **Pre-Populated Clinical Scenarios:**
  - Scenario 1: Eleanor Vance (Buried Penicillin Anaphylaxis)
  - Scenario 2: Arthur Pendelton (Severe Renal Impairment, eGFR 22.4 mL/min)
  - Scenario 3: Clean Baseline (No Contraindications, Safe Discharge)

---

## 📦 4. Git Push Instructions to Hugging Face Spaces
To deploy this Space to your own Hugging Face account:

```bash
# 1. Create a new Space on huggingface.co with SDK: Gradio (free tier)
# 2. Clone your Space repository
git clone https://huggingface.co/spaces/<YOUR_USERNAME>/<YOUR_SPACE_NAME>
cd <YOUR_SPACE_NAME>

# 3. Copy files from hf_space/
cp -r /path/to/CareSentry/hf_space/* .

# 4. Commit and push
git add .
git commit -m "Deploy CareSentry-AI to Hugging Face Spaces"
git push origin main
```

---

## ⚖️ 5. Clinical Safety Disclaimer
**Research tool only.** CareSentry-AI is designed for clinical AI safety research and open-source model inspection. It is not approved for autonomous clinical diagnosis or prescription decision-making. Always verify all medication instructions with a licensed clinician or pharmacist.
