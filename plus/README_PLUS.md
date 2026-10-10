# CareSentry-AI Plus — Extended Clinical Invariant & Attention Observability Suite

> ⚠️ **MANDATORY SAFETY DISCLAIMER**  
> **RESEARCH AND OBSERVABILITY TOOLING ONLY.**  
> CareSentry-AI Plus is designed for AI engineering evaluation and attention observability research. It is **not** a certified Medical Device, clinical diagnostic aid, or clinical decision support system (CDSS). Do not use for real clinical decision-making or direct patient care. All rule packs are marked `reviewer_status: unreviewed` pending formal medical board validation.

---

## 1. Overview & Architectural Philosophy

CareSentry-AI Plus is the **Track B additive extension** to CareSentry-AI. While Track A establishes the core attention prober, model runners, and baseline contraindication linters, Track B introduces advanced clinical invariance, reverse constraint checking, causal validation, interactive visualization, and developer-facing interfaces.

### Golden Rules of Coexistence
- **Strict Namespace Isolation:** All Track B assets reside strictly within `plus/`, `.agents/skills/caresentry-plus/`, `contracts/`, or `.github/workflows/plus-*.yml`.
- **Decoupled Contracts:** Track A and Track B communicate solely via versioned JSON schemas (`contracts/*.schema.json`) and public entrypoints.
- **Adapter Seam:** Feature code never imports `harness.*` directly; all execution routes through `ModelRunnerShim` and `ProbeShim`.
- **Fail-Safe Posture:** Ambiguous clinical assertions trigger verification rather than suppression.

```
                           ┌─────────────────────────────┐
                           │      Patient EHR Record     │
                           └──────────────┬──────────────┘
                                          │
                 ┌────────────────────────┴────────────────────────┐
                 ▼                                                 ▼
   ┌───────────────────────────┐                     ┌───────────────────────────┐
   │ Track A: Base Linter      │                     │ Track B: Plus Engines     │
   │ - Direct Allergy Clashes  │                     │ - RxNorm / ATC Normalizer │
   │ - Simple eGFR Cutoffs     │                     │ - Context & Negation Gate │
   │ (C-01 audit_result.v1)    │                     │ - Cockcroft-Gault / CKD-EPI│
   └─────────────┬─────────────┘                     │ - Cross-Reactivity Packs  │
                 │                                   │ - AGS Beers Criteria      │
                 │                                   │ - Drug-Drug Interactions  │
                 │                                   │ - Reverse Omission Sentry │
                 │                                   └─────────────┬─────────────┘
                 │                                                 │
                 └────────────────────────┬────────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ plus_audit_result.v1 Superset   │
                         │ - Base Verdict                  │
                         │ - Plus Violations               │
                         │ - Reverse Omissions             │
                         │ - Cryptographic Audit Block Hash│
                         └─────────────────────────────────┘
```

---

## 2. Feature Highlights

### F-01: Drug Ontology & Normalization (`plus/src/caresentry_plus/ontology/`)
- Offline dictionary mapping brand names, generics, and clinical abbreviations (PCN, ASA, Bactrim, Augmentin, etc.) to canonical ingredients, RxCUI, and WHO-ATC classes.
- Over **180 alias entries** spanning penicillin, sulfa, NSAID, metformin, spironolactone, and anticoagulant families.
- Lookup latency **< 0.1 ms** (well below the 10 ms target).

### F-02: Extended Invariant Rule Packs (`plus/rule_packs/`)
- Pure JSON rule packs strictly validating against `contracts/rule_pack.v1.schema.json`.
- **Cross-Reactivity:** Penicillin to 1st-generation cephalosporins (BLACTAM epitope caution), sulfonamide antibiotics, and aspirin/AERD cross-sensitivity.
- **Dose-Aware Renal Function:** Computes Cockcroft-Gault Creatinine Clearance (CrCl) and CKD-EPI 2021 eGFR from raw creatinine, age, sex, and weight when eGFR is not stated; enforces strict contraindication thresholds for Metformin, Spironolactone, NSAIDs, and DOACs.
- **AGS Beers Criteria (2023):** Flags high-fall-risk antihistamines, tricyclic antidepressants (TCAs), and benzodiazepines in adults aged $\ge 65$.
- **High-Risk DDIs:** Evaluates Warfarin + NSAIDs, ACEi + Aldosterone Antagonists, Clopidogrel + Omeprazole, and Methotrexate + NSAIDs.
- **Mandatory Provenance:** Every single rule includes external literature citations (`source`, `version`, `citations`).

### F-03: Negation & Context Filter (`plus/src/caresentry_plus/rules/context_filter.py`)
- Evaluates assertion modalities: `AFFIRMED`, `NEGATED`, `HISTORICAL`, `FAMILY_HISTORY`, and `AMBIGUOUS`.
- Tested against a labeled corpus of 65 clinical sentences:
  - **Macro Precision:** 95.4% | **Macro Recall:** 94.4%
  - **Fail-Safe Guarantee:** 100% (Zero active risks suppressed; ambiguous assertions fail safe).

### F-04: Structured Extraction & Reverse Omission Sentry (`plus/src/caresentry_plus/extraction/`)
- Forward Extraction: Structured parsing of demographics, labs, active medications, and diagnoses.
- Reverse Omission Sentry: Verifies whether documented critical constraints (allergies, anticoagulants, severe renal impairment, hyperkalemia) were dropped or ignored by the LLM summary.

### F-05: Evaluation at Scale (`plus/evals/`)
- Deterministic synthetic generator producing **120 test cases** varying needle depth (early 15%, middle 50%, late 85%), distractors, and clinical categories.
- Evaluated with Wilson score 95% confidence intervals:
  - **Violation Recall:** 97.75% (95% CI: [92.17%, 99.38%])
  - **Violation Precision:** 100.00%
  - **False Positive Rate:** 0.00%
  - **Omission Recall (Reverse):** 96.83% (95% CI: [89.14%, 99.13%])
  - **Mitigation Rescue Rate:** 100.00% (95% CI: [96.90%, 100.00%])

### F-06: Interactive Attention Heatmap Viewer (`plus/src/caresentry_plus/viz/`)
- Zero-network, self-contained HTML renderer (no external CDNs or scripts).
- Displays document tokens shaded by attention mass, outlines target needles with glowing borders, highlights control spans, and shows Z-scores.
- Side-by-side comparative mode contrasting baseline vs mitigated attention traces.

### F-07 & F-08: Causal Validation & Per-Head Analysis (`plus/src/caresentry_plus/causal/`)
- Counterfactual needle ablation testing vs control span perturbations.
- Retrieval head discovery across transformer layers; evaluates Track A's terminal 4-layer heuristic against middle-layer induction heads.
- Real empirical calibration report connecting Z-scores to failure likelihood.

### F-09 & F-10: Model Registry & Quantization Study (`plus/models/`, `plus/evals/`)
- Registry (`models/registry.yaml`) indexing 10 open-weight models across Edge, Mid, Medical, and Long-Context tiers.
- FP16 vs NF4 study documenting memory reduction (52–60% VRAM savings) and attention variance.

### F-11: Interactive Gradio Web UI (`plus/webui/app.py`)
- Local dashboard on port 7860.
- Allows pasting EHR records and discharge summaries, running audits, inspecting violations and omissions, and viewing attention heatmaps.

### F-12: MCP Stdio Server & Plus Skill (`plus/mcp_server/`, `.agents/skills/caresentry-plus/`)
- JSON-RPC 2.0 stdio MCP server exposing `audit_plus`, `normalize_drugs`, `omission_check`, and `render_heatmap`.
- Skill specification (`SKILL.md`) under 500 lines compliant with `agent-skills.io/v1`.

### F-13: Cryptographically Hash-Chained Audit Log (`plus/src/caresentry_plus/audit/`)
- Append-only JSONL log where each entry commits to its predecessor via SHA-256 block hashing.
- Privacy-preserving: Stores cryptographic digests of records rather than raw patient narratives (NFR-B6).
- CLI command `caresentry-plus verify-log` flags any tampering, deletion, or modification.

### P2 Extensions
- **F-15 PDF Ingestion:** Offline text extraction with clear error reporting on unscanned rasters.
- **F-16 Multilingual & Readability:** Hindi (हिन्दी) and Spanish (Español) term matching, plus Flesch-Kincaid / Flesch Reading Ease readability scoring.
- **F-17 Mitigation Strategies:** Pure prompt transformation functions (`constraint_repetition`, `retrieval_then_summarize`, `safety_pass_map_reduce`) conforming to Contract C-06.

---

## 3. Quickstart & Usage

### Installation
```bash
# Install Track A base
pip install -e .

# Install Track B Plus in editable mode
pip install -e ./plus
```

### CLI Commands
```bash
# Full audit
caresentry-plus audit --records data/ehr_01.txt --summary data/summary_01.txt

# Reverse omission check
caresentry-plus omission-check --records data/ehr_01.txt --summary data/summary_01.txt

# Drug normalization
caresentry-plus normalize --text "Patient allergic to Augmentin and PCN"

# Render HTML attention heatmap
caresentry-plus render-heatmap --trace-file plus/fixtures/baseline_neglected.trace.json --output heatmap.html

# Verify audit log integrity
caresentry-plus verify-log --log-file plus/evals/results/webui_audit_log.jsonl

# Launch Web UI
caresentry-plus webui --port 7860
```

### Running Test Suites
```bash
# Run Track B test suite (51 passed)
pytest plus/tests

# Run Track A test suite (46 passed)
pytest tests

# Run Ownership Boundary Guard
python plus/tools/check_ownership.py
```

---

## 4. Known Limitations & Research Boundaries

1. **Attention Mass is Necessary, Not Sufficient:** High attention concentration to a clinical constraint does not guarantee factual adherence if the model hallucinates during generation.
2. **Lexical Normalization Boundaries:** Compound brand names in local or foreign markets require inclusion in the offline dictionary; unrecognized entities are flagged for clinician review.
3. **Unreviewed Rule Status:** All invariant rules reflect published literature and FDA guidelines, but remain marked `reviewer_status: unreviewed` until validated by a licensed physician board.
