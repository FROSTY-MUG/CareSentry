---
name: caresentry-guard-audit
description: Deterministic clinical safety invariant verification, prompt-injection defense, constrained decoding, evidence grounding, and patient output pack generation for open-weight medical models.
version: 1.0.0
author: CareSentry Open Team
license: Apache-2.0
standard: agentskills.io/v1
tags:
  - clinical-safety
  - prompt-injection
  - evidence-grounding
  - constrained-decoding
  - open-weight-models
---

# 🩺 CareSentry Guard Agent Skill (`agentskills.io/v1`)

> **Deterministic Defense, Prompt-Injection Scanning, Invariant Verification & Grounding Gateway for Open-Weight Clinical Models.**

CareSentry Guard extends open-weight clinical model harnesses (Qwen2.5, Gemma-2) with a comprehensive defense layer:
1. **Prompt-Injection Defense:** Sanitizes clinical records for adversarial roleplays, system delimiter spoofing, and zero-width steganography without touching legitimate medical negative directives (e.g., "do not give aspirin").
2. **Invariant-Guided Constrained Decoding:** Uses an RxNorm/ATC prefix trie to block generation of contraindicated tokens at the logits level.
3. **Evidence Grounding:** Quantifies sentence-level EHR support to catch hallucinations and phantom lab metrics before discharge.
4. **Deterministic Policy State Machine:** Strictly enforces `VERIFIED`, `ANNOTATED`, `WITHHELD`, or `ABSTAIN` states, escalating to human review if retries fail.
5. **Patient Output Packs:** Generates 6th-grade readability summaries, teach-back questions, and multilingual (Hindi/English) timetables.

---

## 🛠️ Execution & Usage

### 1. Run Complete Guarded Clinical Audit
Audit a raw EHR and model summary with invariant validation, injection check, and evidence grounding:
```bash
python -m caresentry_guard.cli audit --records path/to/ehr.txt --summary path/to/summary.txt --json
```

### 2. Scan Document for Adversarial Injections
Detect hidden instructions, delimiter spoofing, and zero-width characters in discharge notes:
```bash
python -m caresentry_guard.cli scan-injection --doc path/to/note.txt
```

### 3. Generate Patient-Facing Pack
Produces teach-back questions, daily medication timetable, and Flesch-Kincaid readability scoring:
```bash
python -m caresentry_guard.cli patient-pack --summary path/to/verified_summary.txt --patient "Eleanor Vance"
```

### 4. Launch Local OpenAI-Compatible Safety Gateway
Binds to `127.0.0.1:8787` to protect any local application by changing the OpenAI client base URL:
```bash
python -m caresentry_guard.cli serve --port 8787
```

---

## 📋 JSON Output Schema (`guard_audit_result.v1.schema.json`)

```json
{
  "guard_version": "1.0.0",
  "policy_decision": {
    "state": "VERIFIED | ANNOTATED | WITHHELD | ABSTAIN",
    "is_safe_to_release": true,
    "escalate_to_human": false,
    "reasons": ["All clinical invariants passed, zero injection, robust evidence grounding"]
  },
  "injection_audit": {
    "has_injection": false,
    "findings": []
  },
  "grounding_audit": {
    "overall_score": 0.92,
    "safety_critical_violations": 0
  },
  "clinical_linter": {
    "status": "PASS",
    "total_violations": 0
  }
}
```

---

## ⚠️ Safety Disclaimer
*CareSentry Guard is an open-source evaluation and deployment safety harness designed for research and automated auditing. It does not provide medical advice or replace licensed clinician judgement.*
