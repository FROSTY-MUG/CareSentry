# Phase 0 Discovery Document — CareSentry-AI (Track A Audit)

**Date:** 2026-10-10  
**Auditor:** Antigravity IDE-C (Track C Engine)  
**Target Repo Commit:** `0f0fc2b` (v1.0.0-rc1)

---

## 1. Execution & Test Verification

### 1.1 Installation and Test Suite
- **Track A Pytest Execution:**
  ```powershell
  pytest tests/
  ```
  - Result: **23 passed, 1 warning** (`PytestRemovedIn10Warning`) in 16.19 seconds on Windows (Python 3.14.2 / Torch environment).
  - Test files:
    - `tests/test_attention_probe.py` (5 tests) — validates needle span location, control spans sampling, empirical Z-score calculation, telemetry dictionary serialization, and threshold classifications.
    - `tests/test_clinical_linter.py` (10 tests) — validates penicillin allergy, safe macrolides, cephalosporin cross-reactivity, sulfa allergy, renal eGFR < 30 contraindications (metformin, spironolactone), safe normal eGFR, warfarin + NSAID interaction, sub-100ms execution latency, and all 10 synthetic geriatric cases.
    - `tests/test_mitigations.py` (5 tests) — validates system anchor pinning formatting, custom system prompt injection, recency reordering (90th percentile), combined remediation, and attention recovery.
    - `tests/test_self_healer.py` (3 tests) — validates reflection retry loop, temperature step decay ($\Delta T = -0.05$), and maximum cycle exhaustion.

---

## 2. Public Interface Contracts

### 2.1 `harness.model_runner`
- **Class `ModelRunner`:**
  - `__init__(model_id: str = "Qwen/Qwen2.5-1.5B-Instruct", device: str = "auto", quantization: str = "none", force_simulation: bool = False)`
  - `tokenize(prompt: str) -> Tuple[torch.Tensor, List[str]]`
    - Uses `AutoTokenizer` if weights loaded; falls back to Unicode word/punctuation regex `re.findall(r"\w+|[^\w\s]", prompt, re.UNICODE)` in simulation mode.
  - `forward(prompt: str, needle: Optional[str] = None, is_pinned: bool = False, is_recency_reordered: bool = False) -> ForwardPassTelemetry`
- **Class `ForwardPassTelemetry`:**
  - Attributes: `input_ids: torch.Tensor`, `tokens: List[str]`, `seq_len: int`, `num_layers: int`, `num_heads: int`, `attentions: Tuple[Any, ...]`, `is_simulated: bool`.
- **Class `SimulatedAttentionTensor`:**
  - Lazy 4D sliceable tensor representing `(1, num_heads, seq_len, seq_len)` without allocating full $(S \times S)$ dense memory, modeling U-shaped lost-in-the-middle dispersion and recency/anchor boosts.

### 2.2 `harness.attention_probe`
- **Class `AttentionProbe`:**
  - `__init__(runner: Optional[ModelRunner] = None, model_id: str = "Qwen/Qwen2.5-1.5B-Instruct", num_control_spans: int = 20, decision_layers_count: int = 4, random_seed: int = 42)`
  - `locate_needle_span(tokens: List[str], needle: str) -> Tuple[int, int]`
  - `sample_control_spans(seq_len: int, target_start: int, target_end: int, span_len: int, count: int = 20) -> List[Tuple[int, int]]`
  - `compute_span_attention(layer_attentions: Tuple[torch.Tensor, ...], target_layers: List[int], start_idx: int, end_idx: int, seq_len: int) -> float`
  - `probe(prompt: str, needle: str, is_pinned: bool = False, is_recency_reordered: bool = False) -> ProbeResult`
- **Class `ProbeResult`:**
  - Attributes: `model_id: str`, `context_length_tokens: int`, `target_needle: str`, `target_span_tokens: List[int]`, `target_attention_mean: float`, `control_spans_count: int`, `control_attention_mean: float`, `control_attention_std: float`, `z_score: float`, `classification: str`, `layers_analyzed: List[int]`, `mitigation_triggered: bool`, `mitigation_strategy: Optional[str]`, `timestamp: str`.
  - Classification thresholds:
    - $Z \ge 1.0$: `"SUFFICIENTLY_ATTENDED"`
    - $-0.5 \le Z < 1.0$: `"NEUTRAL"`
    - $Z < -0.5$: `"DILUTED"`

### 2.3 `harness.clinical_linter`
- **Functions:**
  - `load_clinical_rules(rules_path: Optional[str] = None) -> Dict[str, Any]`
  - `extract_patient_allergies(raw_text: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]`
  - `extract_renal_metrics(raw_text: str) -> Dict[str, Any]` (returns `{"egfr": float|None, "creatinine": float|None, "raw_matches": ...}`)
  - `find_drugs_in_summary(summary_text: str, drug_list: List[str]) -> List[Tuple[str, str]]`
  - `audit_clinical_safety(raw_ehr: str, summary_content: str, rules: Dict[str, Any]) -> Dict[str, Any]`
  - Exit code: `0` on `"PASS"`, `1` on `"FAIL"`.

### 2.4 `harness.mitigations`
- **Functions:**
  - `apply_anchor_pinning(document: str, constraint: str, system_prompt: Optional[str] = None) -> str`
  - `apply_recency_reordering(document: str, constraint: str, recency_percentile: float = 0.90) -> str`
  - `apply_combined_remediation(document: str, constraint: str, system_prompt: Optional[str] = None) -> str`

### 2.5 `harness.self_healer`
- **Class `SelfHealingLoop`:**
  - `__init__(rules: Optional[Dict[str, Any]] = None, max_cycles: int = 3, initial_temperature: float = 0.70, temperature_step: float = -0.05)`
  - `run(raw_ehr: str, initial_summary: str, generator_callback: Optional[Callable[[str, str, float], str]] = None) -> ReflectionResult`

---

## 3. Data Schemas & Reference Structures

### 3.1 `clinical_rules.json`
- Root keys:
  - `version: str` ("1.0.0")
  - `name: str`
  - `allergies: list` (objects with `allergy_class`, `aliases`, `contraindicated_drugs`, `cross_reactive_drugs`, `severity`, `mechanism`)
  - `renal_clearance_thresholds: list` (objects with `drug_name`, `aliases`, `egfr_cutoff_ml_min`, `operator`, `action`, `severity`, `rationale`)
  - `drug_drug_interactions: list` (objects with `drug_a`, `drug_b`, `severity`, `rationale`)

### 3.2 Output Shape of `audit_clinical_safety`
```json
{
  "status": "PASS" | "FAIL",
  "total_violations": 0,
  "violations": [
    {
      "type": "ALLERGY_CONTRAINDICATION" | "RENAL_THRESHOLD_VIOLATION" | "DRUG_DRUG_INTERACTION",
      "severity": "CRITICAL" | "HIGH",
      "offending_drug": "string",
      "evidence_in_summary": "string snippet",
      "patient_allergy_evidence": "string snippet",
      "mechanism": "string",
      "recommendation": "string"
    }
  ],
  "passed_checks_count": 0,
  "passed_checks": [],
  "renal_metrics": { "egfr": 22.4, "creatinine": 2.9 },
  "execution_time_ms": 0.45,
  "standard": "agent-skills.io/v1"
}
```

---

## 4. Hardware and Latency Profile
- Linter execution time: 0.15ms – 2.5ms on modern CPU.
- Model runner: Automatically enters high-fidelity lazy tensor simulation if GPU / Hugging Face remote weights are absent or air-gapped, enabling instant sub-second verification.
