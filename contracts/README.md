# CareSentry Integration Contracts (Shared)

This directory contains versioned, immutable JSON schemas and interface contracts shared between Track A (Core Harness) and Track B (CareSentry-AI Plus).

## Golden Rules for Contracts

1. **Immutable Once Frozen**: Once a contract version is confirmed (e.g., `*.v1.*`), it is frozen. Never edit a contract in-place.
2. **Additive Evolution**: To introduce breaking changes or modifications, create `*.v2.*` alongside `*.v1.*`.
3. **Decoupled Architecture**: Track A and Track B communicate strictly through these versioned contracts and public entry points.
4. **Change Requests**: All inter-track coordination requests are filed under `requests/` following the naming convention `B-NNNN-<title>.md` (from Track B) or `A-NNNN-<title>.md` (from Track A).

## Active Contracts

| Contract File | Producer | Consumer | Description |
| :--- | :--- | :--- | :--- |
| `audit_result.v1.schema.json` | Track A | Track B | Output schema of Track A deterministic invariant linter (`audit_contraindication.py`) |
| `attention_trace.v1.schema.json` | Track A | Track B | Attention telemetry and token attribution trace emitted via `--dump-trace` |
| `plus_audit_result.v1.schema.json` | Track B | Evaluators / UI / MCP | Superset audit output incorporating base audit, plus violations, omissions, and context flags |
| `rule_pack.v1.schema.json` | Track B | Track B / Evaluators | Format specification for invariant rule packs with mandatory provenance metadata |
| `mitigation_strategy.v1.md` | Track B | Track A / Track B | Specification for prompt mitigation pure functions `(PromptParts) -> PromptParts` |
