# Security & Safety Policy

## 1. Clinical & Medical AI Safety Disclaimer
`CareSentry-AI` is an open-source evaluation and testing harness developed for research, benchmarking, and developer observability purposes.

**DO NOT USE THIS SOFTWARE FOR DIRECT CLINICAL DECISION-MAKING ON REAL PATIENTS WITHOUT HUMAN CLINICAL SUPERVISION.**

This tool is intended to catch errors in language models; it does not replace a licensed medical practitioner, pharmacist, or clinical safety board.

## 2. Patient Data & Privacy (HIPAA / GDPR Compliance)
* All datasets included in the `data/` directory (`synthetic_geriatric_cases.json`) are **100% synthetically generated** and contain no real Protected Health Information (PHI).
* The `CareSentry-AI` harness is designed for **air-gapped, fully local inference**. When run using local open-weight models (via Hugging Face `transformers` or `vLLM`), zero prompt tokens, clinical notes, or attention telemetry leave the local compute environment.

## 3. Reporting a Security Vulnerability
If you discover a security vulnerability or a bypass in the deterministic safety linter:
1. **Do not open a public GitHub issue.**
2. Send a detailed vulnerability report to the repository maintainers via security advisory or email at: `security@caresentry.local`.
3. Include reproducible prompt payloads, model configurations, and expected vs. actual linter behavior.
4. The team will acknowledge receipt within 24 hours and issue a remediation patch within 72 hours.
