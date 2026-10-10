# Handoff Request B-0003: Mitigation Registry in `harness/mitigations.py`

**From:** Track B (Antigravity IDE-B)  
**To:** Track A (Core Harness IDE-A)  
**Status:** Open / Proposed at Checkpoint 1  
**Category:** Pluggable Strategies  

## Summary
Expose a `STRATEGIES` dictionary and a `register_strategy(name, func)` function in `harness/mitigations.py` conforming to contract `contracts/mitigation_strategy.v1.md`.

## Rationale
Enables Track B's additional mitigation strategies (F-17: Constraint Repetition, Retrieval-Then-Summarize, Safety Pass Map-Reduce) to be registered dynamically in Track A's self-healing loop.

## Proposed Minimal Change (Track A)
```python
STRATEGIES = {
    "system_anchor_pinning": apply_anchor_pinning,
    "recency_reordering": apply_recency_reordering,
}

def register_strategy(name: str, strategy_func):
    STRATEGIES[name] = strategy_func
```

## Track B Fallback While Waiting
Track B ships strategies as standalone pure functions in `caresentry_plus.strategies`. No integration is required for Track B to operate independently.
