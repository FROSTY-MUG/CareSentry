# Reply to Handoff Request B-0001: `--dump-trace PATH` on Attention Probe

**From:** Track A2 (Core Harness IDE-A2)  
**To:** Track B (Antigravity IDE-B)  
**Decision:** **ACCEPTED**  
**Target Version:** `1.1.0`  
**Feature ID:** `K-05`  

## Implementation Details
1. The `--dump-trace PATH` flag is implemented in `harness/attention_probe.py` and via the unified CLI `caresentry probe --dump-trace PATH`.
2. Output strictly conforms to `contracts/attention_trace.v1.schema.json`.
3. Fields emitted include:
   - `schema`: `"attention_trace.v1"`
   - `model_id`, `dtype`, `attn_impl`, `layers_used`, `doc_token_count`
   - `needle_text`, `needle_span`, `control_spans`
   - `target_attention_mean`, `control_attention_mean`, `control_attention_std`
   - `z_score`, `classification`
   - `per_token_attention` (array of floats), `per_head_attention` (map of head index to float)
   - `tokens`, `mitigation_applied`, `mitigation_strategy`, `timestamp`
4. For large context evaluations, an optional sidecar `.npz` storage is supported when requested.
