# Track C Working Assumptions (`ASSUMPTIONS.md`)

This document records the foundational architectural assumptions governing Track C (`caresentry_guard`):

1. **Air-Gap / Offline Execution (NFR-C1):**
   - All runtime execution (linter, proxy gateway, constrained decoding, grounding, de-identification) must run strictly offline with 0 network calls.
   - Any external model weights or ontologies are pre-downloaded or offline-simulated.

2. **Track A Immutability:**
   - Track A files are read-only and imported only via `guard/src/caresentry_guard/adapters/*.py`.
   - Track C can only make verdicts **stricter** (e.g. converting a Track A `PASS` into `FAIL` or `ANNOTATED` due to injection, ungrounded hallucination, or low confidence), never more lenient.

3. **Track B Independence:**
   - Track B paths (`plus/**`, `contracts/**`, etc.) are completely reserved and untouched.
   - If Track B ontology is importable at runtime (`try: import caresentry_plus.ontology`), Track C can optionally leverage it, but never requires it.

4. **Safety Gateway Port:**
   - The safety gateway binds strictly to `127.0.0.1:8787` (localhost only).

5. **Deterministic Testing:**
   - All benchmarks, evaluation sweeps, and mutation fuzzers use seeded random number generators (seed 42) for 100% reproducibility across environments.
