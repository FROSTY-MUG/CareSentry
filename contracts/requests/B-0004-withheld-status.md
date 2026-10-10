# Handoff Request B-0004: Explicit `WITHHELD` Verdict on Retry Exhaustion

**From:** Track B (Antigravity IDE-B)  
**To:** Track A (Core Harness IDE-A)  
**Status:** Open / Proposed at Checkpoint 1  
**Category:** Clinical Safety Posture  

## Summary
When the self-healing reflection retry loop in `harness/self_healer.py` exhausts its maximum retry budget (default 3 retries) and invariant violations persist, emit a status of `WITHHELD` instead of returning the last failing summary.

## Rationale
In accordance with NFR-B5 (Safety Posture) and clinical zero-tolerance design, a discharge summary containing unresolvable lethal contraindications should be formally marked withheld rather than emitted with a failing grade.

## Proposed Minimal Change (Track A)
In `harness/self_healer.py`, set `result.status = "WITHHELD"` when `retries >= max_retries` and violations remain.

## Track B Fallback While Waiting
Track B treats repeated `FAIL` verdicts from Track A as `WITHHELD` within Track B's own UI (F-11) and CLI/MCP outputs, applying the safety gate unilaterally.
