# Handoff Request B-0001: Optional `--dump-trace PATH` on Attention Probe

**From:** Track B (Antigravity IDE-B)  
**To:** Track A (Core Harness IDE-A)  
**Status:** Open / Proposed at Checkpoint 1  
**Category:** Telemetry & Observability  

## Summary
Add an optional command-line flag `--dump-trace PATH` to `harness/attention_probe.py` that serializes the forward-pass token attention distribution and telemetry to `contracts/attention_trace.v1.schema.json`.

## Rationale
Features F-06 (Attention Heatmap Viewer), F-07 (Causal Validation), and F-08 (Per-Head Analysis) consume attention distributions to verify whether low Z-scores causally trigger omissions and contraindications.

## Proposed Minimal Change (Track A)
In `harness/attention_probe.py`, when `--dump-trace` is passed, write `ProbeResult` along with `per_token_attention` and `per_head_attention` to the requested path in JSON format matching `contracts/attention_trace.v1.schema.json`.

## Track B Fallback While Waiting
Track B develops against frozen traces in `plus/fixtures/*.trace.json`. Heatmap and causal analysis tools accept `--trace-file` input directly, requiring zero runtime changes to Track A if this flag is not implemented.
