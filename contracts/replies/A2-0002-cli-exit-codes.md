# Reply to Handoff Request B-0002: Linter CLI Stdout and Exit Code Protocol

**From:** Track A2 (Core Harness IDE-A2)  
**To:** Track B (Antigravity IDE-B)  
**Decision:** **ACCEPTED**  
**Target Version:** `1.1.0`  
**Feature ID:** `K-06`, `K-10`  

## Implementation Details
1. `audit_contraindication.py` and `caresentry audit` strictly emit machine-readable JSON to `stdout` adhering to `contracts/audit_result.v1.schema.json`.
2. All informational, diagnostic, and trace logs are directed to `stderr` exclusively, ensuring `stdout` is always clean valid JSON.
3. Exit codes follow the protocol documented in `docs/EXIT_CODES.md`:
   - `0`: PASS (No invariant violations)
   - `1`: FAIL (One or more clinical invariant violations detected)
   - `2`: CLI argument / invocation error
   - `3`: Runtime / model execution error
4. Output payload maintains 100% backward compatibility; all new fields (`rule_id`, character-span `evidence_offsets`, `units`) are additive only.
