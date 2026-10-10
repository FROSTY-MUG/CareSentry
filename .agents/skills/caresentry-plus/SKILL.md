---
name: caresentry-plus-audit
description: Offline clinical safety invariant suite applied when deeper checks are requested: omissions, interactions, dose-aware renal, or attention causal validation.
license: Apache-2.0
compatibility: posix, win32, python>=3.10
allowed-tools: python bash pwsh
metadata:
  standard: agent-skills.io/v1
  category: clinical-safety-engineering
---

# CareSentry-AI Plus Audit Skill

## Overview
CareSentry-AI Plus provides additive clinical safety invariants and observability tooling extending baseline contraindication checks. While baseline checks focus on direct drug-allergy clashes, CareSentry-AI Plus activates extended clinical verification:
- **Reverse Omission Gate**: Verifies whether documented critical constraints (allergies, anticoagulants, renal impairment) were omitted from the discharge summary.
- **Cross-Reactivity Invariants**: Flags beta-lactam, sulfonamide, and aspirin-NSAID cross-reactivity based on biochemical homology.
- **Dose-Aware Renal Clearance**: Calculates CrCl (Cockcroft-Gault) and eGFR (CKD-EPI 2021) to enforce dosing cutoffs for metformin, spironolactone, NSAIDs, and DOACs.
- **AGS Beers Criteria & Drug Interactions**: Protects older adults (>=65) from high anticholinergic burden and flags lethal interaction pairs.
- **Attention Heatmaps & Causal Validation**: Generates interactive HTML token attention distributions and validates empirical Z-scores against counterfactual needle ablations.

## When to Use
Execute this skill when deeper clinical checks are requested:
1. When discharge summaries must be checked for dropped/omitted constraints (reverse safety verification).
2. When evaluating complex multi-drug regimens for drug-drug interactions or duplicate therapy.
3. When creatinine or demographics are present without explicit eGFR, requiring calculated clearance.
4. When visual attention heatmap inspection or empirical Z-score telemetry is required.

## Execution

### 1. Execute Deep Clinical Invariant Audit
Run the CLI audit entrypoint:

```bash
python .agents/skills/caresentry-plus/scripts/audit_plus_cli.py \
  --records <path_to_raw_ehr.txt> \
  --summary <path_to_generated_summary.txt> \
  --json
```

Or via the installed package CLI:

```bash
caresentry-plus audit --records <path_to_ehr> --summary <path_to_summary>
```

### 2. Interpret Structured Output
The audit emits structured JSON adhering to `contracts/plus_audit_result.v1.schema.json`:

```json
{
  "schema": "plus_audit_result.v1",
  "status": "PASS | FAIL",
  "base": { "...Track A C-01 output verbatim..." },
  "plus_violations": [
    {
      "rule_id": "PLUS-CROSS-01",
      "type": "cross_reactivity",
      "severity": "HIGH",
      "message": "Potential beta-lactam cross-reactivity...",
      "offending_drug": "Cephalexin",
      "provenance": { "source": "JAMA 2019", "reviewer_status": "unreviewed" }
    }
  ],
  "omissions": [
    {
      "category": "ALLERGY_CONSTRAINT",
      "constraint": "Documented PENICILLIN Allergy omitted from discharge summary.",
      "severity": "CRITICAL",
      "remediation": "Explicitly document allergy in discharge plan."
    }
  ],
  "audit_log_ref": "sha256_hash"
}
```

- **`status: "PASS"`**: No base violations, no high-severity invariant breaches, and zero critical constraint omissions.
- **`status: "FAIL"`**: One or more safety invariants breached. The summary must be withheld or regenerated with pinned constraints.

## Safety Disclaimer
RESEARCH AND OBSERVABILITY TOOLING ONLY. Not for clinical decision-making or diagnosis.
