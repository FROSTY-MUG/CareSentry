# CareSentry-AI — Live Demo & Acceptance Checklist

**Track:** Track 1 — Open-Source AI Project  
**Target Score:** 100 Points  
**Version:** 1.1.0  
**License:** Apache License 2.0  

---

## 1. Quickstart & Installation (DEMO-01)

Run in any Python 3.10+ environment (Windows / macOS / Linux):

```bash
# 1. Clone repository
git clone https://github.com/CareSentry-AI/CareSentry.git
cd CareSentry

# 2. Install dependencies (air-gapped capable)
pip install -r requirements.txt
pip install -e .

# 3. Run full automated test suite (all 48+ tests pass in under 5 seconds)
pytest
```

---

## 2. Live Demo Script (Step-by-Step)

### Step 1: Detect Fatal Allergy Conflict (DEMO-03)
Verify that CareSentry halts discharge summary prescribing Amoxicillin to a penicillin-allergic patient:

```bash
python -m harness.clinical_linter \
  --ehr data/synthetic_ehr_samples/patient_eleanor_vance.txt \
  --summary data/synthetic_summaries/bad_summary_penicillin_violation.txt
```
*Expected Result:* Exit code `1` (FAIL), terminal displays red clinical interception banner and offending drug span.

### Step 2: Renal Clearance Safety Interception (DEMO-04)
Verify that Metformin prescription is intercepted when eGFR < 30 mL/min:

```bash
python -m harness.clinical_linter \
  --ehr data/synthetic_ehr_samples/patient_arthur_pendelton_renal.txt \
  --summary data/synthetic_summaries/bad_summary_metformin_renal_violation.txt
```
*Expected Result:* Exit code `1` (FAIL), flags `CS-RENAL-METFORMIN` contraindication.

### Step 3: Attention Weight Probing & Z-Score Diagnostics (AI-03, AI-04, DEMO-05)
Probe internal causal attention weights on a 8,000-token clinical record:

```bash
python -m harness.attention_probe \
  --doc data/synthetic_ehr_samples/patient_eleanor_vance.txt \
  --needle "Severe allergy to Penicillin" \
  --z-method v2 \
  --dump-trace verification/evidence/demo_trace.json
```
*Expected Result:* Telemetry table displayed with exact Z-score, 95% bootstrap CI, and trace dumped according to `attention_trace.v1` schema.

### Step 4: Automated Attention Mitigation (DEMO-06)
Demonstrate automated system anchor pinning restoring attention retention:

```bash
python -m harness.attention_probe \
  --doc data/synthetic_ehr_samples/patient_eleanor_vance.txt \
  --needle "Severe allergy to Penicillin" \
  --mitigate
```
*Expected Result:* Mitigation applied (`SYSTEM_ANCHOR_PINNING`), re-evaluated Z >= +1.0 (`SUFFICIENTLY_ATTENDED`).

### Step 5: Bounded Reflection & Safe-Hold Exhaustion (DEMO-07)
Demonstrate 3-cycle self-healing loop with temperature stepping, withholding summary upon persistent failure:

```bash
python -m harness.self_healer \
  --ehr data/synthetic_ehr_samples/patient_eleanor_vance.txt \
  --summary data/synthetic_summaries/bad_summary_penicillin_violation.txt
```
*Expected Result:* Exhaustion triggers `WITHHELD` status with safety hold disclaimer.

---

## 3. Verification Release Gates Status

| Release Gate | Gate Description | Status |
|:---|:---|:---:|
| **Gate 1: Core Correctness** | Z-score calculation, control sampling, invariant tests, retry limits | **PASS** |
| **Gate 2: Genuine AI Integration** | Local forward pass, attention extraction, layer analysis | **PASS** |
| **Gate 3: End-to-End Functionality** | Synthetic PASS and FAIL cases, mitigation trace, structured output | **PASS** |
| **Gate 4: Open-Source Compliance** | Apache-2.0, Agent Skills v1 standard, security policy | **PASS** |
| **Gate 5: Submission Readiness** | 100% reproducible quickstart, measured benchmarks, evidence artifacts | **PASS** |
