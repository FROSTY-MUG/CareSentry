---
name: caresentry-audit
description: Offline clinical safety verification and attention-anchoring gate for medical discharge summaries. Catches neglected allergies, drug interactions, and renal dosage violations in open-weight models.
license: Apache-2.0
compatibility: posix, python>=3.10
allowed-tools: python bash
metadata:
  standard: agent-skills.io/v1
  category: clinical-safety-engineering
---

# CareSentry Audit Skill

## Overview
CareSentry-AI provides a deterministic, offline verification invariant gate and attention-anchored sentry harness for open-weight clinical language models (such as Qwen2.5 and Gemma-2). When processing lengthy geriatric EHR packets, open-weight models can drop critical negative constraints due to the "Lost-in-the-Middle" phenomenon. This skill protects patient safety by enforcing hard deterministic checks and empirical attention telemetry.

## When to Use
Execute this skill whenever an autonomous agent, clinical workflow, or medical assistant model processes electronic health records (EHRs), laboratory chemistry panels, or hospital discharge summaries to generate patient-facing instructions or medication regimens.

## Verification Pipeline

### 1. Execute Offline Deterministic Invariant Checker
Run the sub-100ms offline invariant linter:

```bash
python .agents/skills/caresentry/scripts/audit_contraindication.py \
  --records <path_to_raw_ehr.txt> \
  --summary <path_to_generated_summary.json>
```

Or via the POSIX wrapper:
```bash
bash .agents/skills/caresentry/scripts/run_probe.sh \
  --records <path_to_raw_ehr.txt> \
  --summary <path_to_generated_summary.json>
```

### 2. Interpret Structured Output
The linter emits structured JSON:
- **`status: "PASS"`**: No allergy conflicts or renal dosing threshold violations detected. Safe to deliver summary to patient/caregiver.
- **`status: "FAIL"`**: One or more clinical safety invariants were violated. Inspect the `violations` array:
  - `type`: `ALLERGY_CONTRAINDICATION` | `RENAL_THRESHOLD_VIOLATION` | `DRUG_DRUG_INTERACTION`
  - `offending_drug`: The contraindicated medication name
  - `recommendation`: Specific clinical corrective directive

### 3. Agent Self-Healing Reflection Loop
If the status is `FAIL`, do NOT output the draft summary. Instead, re-prompt the generative model with the reflection message:
```text
CRITICAL SAFETY VIOLATION: The patient records show [VIOLATION]. Remove the contraindicated medication immediately and re-verify.
```
Apply temperature reduction ($\Delta T = -0.05$) per retry attempt (up to 3 cycles).

## Attention Z-Score Gate
When running under the CareSentry Model Harness (`harness.attention_probe`):
- Cross-layer multi-head attention weights are probed across the final 4 decision layers.
- The target constraint is statistically benchmarked against 20 randomized control spans of equal length:
  $$Z = \frac{\bar{A}_{\text{target}} - \mu_{\text{controls}}}{\sigma_{\text{controls}} + 10^{-9}}$$
- **$Z \ge +1.0$**: Sufficiently Attended (Constraint firmly anchored in model attention).
- **$-0.5 \le Z < +1.0$**: Neutral / Ambiguous.
- **$Z < -0.5$**: Attention Dilution detected. Triggers automated prompt remediation:
  - **System Anchor Pinning**: Elevates the negative constraint to terminal system instructions.
  - **Recency Reordering**: Relocates middle-depth clinical constraints into the final 10% recency zone.
