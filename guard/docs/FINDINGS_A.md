# Track A Audit Findings & Architectural Gaps (`FINDINGS_A.md`)

This document records vulnerabilities, edge-case failures, and architectural limitations identified in Track A (`v1.0.0-rc1`).  
Per the Track C core rules, Track A code is **never modified in-place**. Track C creates adapters and defensive safeguards that harden, wrap, or strictly supersede these behaviors.

---

## Finding 1: EHR Allergy Negation False-Positive (CS-FIND-001)
- **Severity:** HIGH
- **Component:** `harness/clinical_linter.py::extract_patient_allergies`
- **Description:** The allergy extraction regex in Track A does not check for negation in the EHR narrative. Phrases such as `"Allergies: No known drug allergies"`, `"No penicillin allergy"`, or `"Penicillin allergy ruled out by skin testing"` match the regex pattern `rf"(?:allerg(?:y|ies|ic)\s*(?:to|:)?\s*[\w\s,;-]{{0,30}}?\b{escaped}\b)"` because `"allerg... to penicillin"` appears in the text.
- **Reproduction:**
  ```python
  from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
  ehr = "Patient examined. Allergies: No known allergy to penicillin. Skin test negative."
  summary = "Prescribe Amoxicillin 500mg PO TID."
  rules = load_clinical_rules()
  res = audit_clinical_safety(ehr, summary, rules)
  print(res["status"])  # Emits FAIL with ALLERGY_CONTRAINDICATION
  ```
- **Expected:** The patient explicitly has NO allergy; the linter should recognize negation and not flag amoxicillin as an allergy violation.
- **Actual:** Flagged as a CRITICAL violation.
- **Track C Mitigation:** Track C introduces contextual negation scoping (G-03/G-04/G-11) in its pre-flight validation adapter to accurately distinguish affirmative allergies from negated assertions.

---

## Finding 2: Needle Location Fallback Bias in `locate_needle_span` (CS-FIND-002)
- **Severity:** MEDIUM
- **Component:** `harness/attention_probe.py::locate_needle_span`
- **Description:** When exact token sequence and character substring matching fail (e.g. due to subword token boundaries, punctuation normalization, or formatting differences), the probe falls back to `mid = seq_len // 2`.
- **Reproduction:**
  If a needle is placed at the 15% depth mark (beginning) and contains unusual unicode apostrophes or line breaks:
  `mid = seq_len // 2` assigns the needle span to the 50% depth position.
- **Expected:** Raise an explicit error, use fuzzy token alignment, or report exact needle unlocatability.
- **Actual:** Measures attention on an arbitrary middle control text, falsely reporting severe attention dilution ($Z < -0.5$).
- **Track C Mitigation:** `a_probe.py` provides resilient subword-aware sequence matching and fuzzy levenshtein/character span anchoring before fallback.

---

## Finding 3: Lack of Dose-Awareness and Cockcroft-Gault / CKD-EPI Calculation (CS-FIND-003)
- **Severity:** HIGH
- **Component:** `harness/clinical_linter.py::extract_renal_metrics`
- **Description:** Renal threshold checking depends entirely on an explicit stated `"eGFR < 30"` or regex match for `egfr`. Real clinical discharge notes often document only raw laboratory chemistries (Serum Creatinine, Age, Sex, Weight). Furthermore, some drugs are permitted at reduced doses (e.g. Metformin 500mg daily if eGFR 30-45; Gabapentin renal titration) rather than being universally contraindicated.
- **Expected:** Calculate estimated clearance using Cockcroft-Gault ($CrCl = \frac{(140 - \text{age}) \times \text{weight}}{72 \times S_{Cr}} \times (0.85 \text{ if female})$) and verify dosage ceilings.
- **Actual:** Any document lacking an explicit `eGFR: <num>` string bypasses the renal guard completely.
- **Track C Mitigation:** Track C's invariant engine includes mathematical clearance calculators and dose-ceiling parsing.

---

## Finding 4: Incomplete Drug Class Ontology & Spelling Fragility (CS-FIND-004)
- **Severity:** HIGH
- **Component:** `.agents/skills/caresentry/references/clinical_rules.json`
- **Description:** The clinical rules matrix hardcodes ~14 penicillin-related strings. Minor typos ("Augmntin", "Amoxil-clav"), generic formulation variations ("amoxicillin with clavulanate potassium"), or brand-to-generic mappings missing from the JSON bypass the string matcher.
- **Reproduction:**
  `summary = "Discharge orders: Take Augmntin 875mg PO BID."`
  Result: Passes without detecting penicillin allergy clash!
- **Track C Mitigation:** Track C implements `LexiconProvider` (G-04) incorporating phonetic matching, Levenshtein distance, and standardized ATC/RxNorm ontology trees.

---

## Finding 5: Attention Weight Correlation is Non-Causal (CS-FIND-005)
- **Severity:** CRITICAL (Methodological / Reviewer Risk)
- **Component:** `harness/attention_probe.py`
- **Description:** Measuring raw multi-head attention to a token span does not prove whether the model actually decoded or ignored the information (attention is not explanation). Attention sinks (token 0, punctuation) often absorb high attention without semantic utility. Conversely, information can be routed into the residual stream in intermediate layers (layers 12–16) and used downstream with low direct attention in the final 4 layers.
- **Expected:** Provide causal validation such as ablation testing (ablating the needle span to observe output probability deltas) and linear probing of hidden states.
- **Track C Mitigation:** Feature G-06 (Hidden-State Linear Probes) and G-08 (Inference-time attention steering) empirically prove whether information is linearly accessible in representation space.

---

## Finding 6: Self-Healer String Substitution Overlap (CS-FIND-006)
- **Severity:** MEDIUM
- **Component:** `harness/self_healer.py::_deterministic_repair`
- **Description:** Case-insensitive substring replacement `summary.replace(offending, substitute)` produces syntactically malformed orders:
  Input: `"Prescribe Amoxicillin 500 mg PO TID for 7 days."`
  Replacement: `"Prescribe Azithromycin 250 mg PO daily 500 mg PO TID for 7 days."` (dangling conflicting dosage).
- **Track C Mitigation:** Track C uses regex-aware dosage replacing and structured prescription formatting.
