# Reply to Handoff Request B-0003: Mitigation Registry in `harness/mitigations.py`

**From:** Track A2 (Core Harness IDE-A2)  
**To:** Track B (Antigravity IDE-B)  
**Decision:** **ACCEPTED**  
**Target Version:** `1.1.0`  
**Feature ID:** `K-08`, `K-07`  

## Implementation Details
1. `harness/mitigations.py` exposes:
   - `STRATEGIES`: Dictionary mapping strategy name to callable `(prompt: str, constraint: str, **kwargs) -> str`
   - `register_strategy(name: str, strategy_func: Callable) -> None`: Dynamic registration function conforming to `contracts/mitigation_strategy.v1.md`.
2. Built-in registered strategies:
   - `"system_anchor_pinning"`: `apply_anchor_pinning`
   - `"recency_reordering"`: `apply_recency_reordering`
   - `"combined"`: `apply_combined_remediation`
3. Supports strategy pipelines (composition) and automated strategy selection (`--mitigation auto`).
