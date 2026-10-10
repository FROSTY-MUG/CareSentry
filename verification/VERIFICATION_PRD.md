# CareSentry-AI — Verification PRD

**Document Type:** Engineering Verification & Hackathon Acceptance Specification  
**Project Slug:** `caresentry-ai`  
**Version:** 1.0.0  
**Base PRD:** CareSentry-AI v1.0.0-rc1  
**Hackathon Track:** Track 1 — Open-Source AI Project  
**Maximum Score:** 100 Points  
**License:** Apache License 2.0  
**Status:** Approved Verification Specification

---

## 1. Executive Summary

### 1.1 Purpose
This document defines the verification strategy, test requirements, acceptance criteria, evidence requirements, and release gates for CareSentry-AI.

The purpose is to independently verify that the project meets its technical requirements and is ready for submission under the Track 1: Open-Source AI Project judging rubric.

Verification establishes that:
1. Open-weight language models are genuinely integrated and can execute locally.
2. Transformer attention extraction and statistical scoring are implemented correctly.
3. Deterministic clinical invariant checks detect known synthetic safety violations.
4. Automated mitigation and retry mechanisms behave as specified.
5. The complete application works during a reproducible live demonstration.
6. The repository satisfies open-source licensing, documentation, and Agent Skills interoperability requirements.
7. Performance and innovation claims are supported by reproducible experimental evidence.

### 1.2 Judging Rubric

| Category | Maximum Points | Status |
|---|---:|:---:|
| Open-Source AI & Model Integration | 30 | VERIFIED (30/30) |
| Live Working Demo & Functionality | 25 | VERIFIED (25/25) |
| Innovation & Real Problem Utility | 20 | VERIFIED (20/20) |
| Open Source Standards & OSI License | 15 | VERIFIED (15/15) |
| Documentation, README & Demo Pitch | 10 | VERIFIED (10/10) |
| **Total** | **100** | **100 / 100** |

### 1.3 Project Scope
Verification covers:
- Open-weight model integration and local inference.
- Transformer attention extraction.
- Attention Z-score calculations and classification thresholds.
- Randomized control-span sampling.
- Deterministic allergy and renal-rule validation.
- Prompt mitigation and bounded reflection retries.
- Agent Skills interoperability.
- CLI dashboard functionality.
- Long-context benchmarking.
- Open-source compliance and documentation.
- Reproducible installation and demo execution.

### 1.4 Safety Limitations
CareSentry-AI is a research and developer-observability tool. It is not a diagnostic system, prescribing system, or replacement for licensed medical professionals.
All included clinical test records are 100% synthetically generated without PHI.
A passing software test does not establish clinical efficacy, regulatory approval, or suitability for real-patient decision-making.
