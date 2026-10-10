# Handoff Request B-0002: Linter CLI Stdout and Exit Code Protocol

**From:** Track B (Antigravity IDE-B)  
**To:** Track A (Core Harness IDE-A)  
**Status:** Open / Proposed at Checkpoint 1  
**Category:** Linter CLI Contract Confirmation  

## Summary
Confirm that `audit_contraindication.py --records R --summary S` and `clinical_linter.py` maintain stdout JSON adhering to `contracts/audit_result.v1.schema.json`, and strictly return exit code 0 for `PASS` and non-zero (1) for `FAIL`.

## Rationale
Used by Track B's extended audit runner (F-02), Web UI (F-11), and MCP server (F-12) to execute Track A's base checks via subprocess without importing internals.

## Proposed Minimal Change (Track A)
No change needed if current behavior is maintained: verify that errors or diagnostic logs are emitted to `stderr` rather than `stdout`, ensuring stdout remains valid JSON.

## Track B Fallback While Waiting
Track B parses stdout using a best-effort JSON extractor that strips any leading/trailing diagnostic messages.
