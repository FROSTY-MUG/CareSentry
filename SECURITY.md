# Security & Clinical Safety Policy

## 1. Clinical & Medical AI Safety Disclaimer

**CareSentry-AI** (`caresentry-ai`) is an open-source evaluation framework, attention sentry, and deterministic verification harness engineered for AI research, benchmarking, and developer observability.

> [!CAUTION]
> **NOT FOR DIRECT UNMONITORED CLINICAL DECISION-MAKING.**
> CareSentry-AI is designed to audit and catch errors in open-weight language models. It does NOT replace the professional judgment of a licensed physician, registered nurse, clinical pharmacist, or hospital clinical review board.

---

## 2. Patient Data Privacy & Zero-Cloud Guarantee (HIPAA / GDPR)

1. **100% Synthetic Evaluation Data**: All patient discharge records, laboratory panels, and case files located in `data/` (`synthetic_geriatric_cases.json`, `synthetic_15_verification_cases.json`) are completely synthetic, fictitious profiles created for algorithmic verification. They contain **zero real Protected Health Information (PHI)**.
2. **Local Air-Gapped Inference**: CareSentry-AI runs strictly against local Hugging Face checkpoints or local gateway instances. Zero prompt tokens, clinical notes, or attention telemetry are transmitted to external cloud inference APIs (no OpenAI, Anthropic, or third-party inference endpoints).
3. **No Persistent PHI Logging**: The gateway and web UI do not write patient record text into persistent logs. Session memory is ephemeral and retained only in local volatile RAM.

---

## 3. Defense-in-Depth Security Invariants

CareSentry-AI incorporates proactive defensive filters at the gateway boundary:

### 3.1 Prompt Injection & Steganography Scanning
- **Delimiter Spoofing**: Blocks malicious attempts to terminate clinical prompts using synthetic `[SYSTEM]`, `<|im_end|>`, or `--- END PATIENT RECORD ---` sequences.
- **Instruction Overrides**: Intercepts phrases attempting to bypass clinical guidelines (e.g., *"Ignore previous safety instructions"*).
- **Zero-Width Steganography**: Scans for and strips hidden Unicode zero-width spaces (`\u200B`, `\u200C`, `\u200D`, `\uFEFF`) used to smuggle adversarial payloads through medical text.

### 3.2 Monotonic Safety Architecture
- The plugin architecture enforces strict monotonic safety: external extensions or adapters can add additional safety violations, but are **cryptographically and architecturally barred from converting a `FAIL` verdict into a `PASS`** or suppressing existing clinical violations.

### 3.3 Cryptographic Audit Trail
- Every verification audit generates a deterministic SHA-256 block hash chaining previous audit states, guaranteeing immutable records of all safety intercepts.

---

## 4. Coordinated Vulnerability Disclosure

If you identify a security flaw, prompt injection bypass, or safety linter evasion:

1. **Do not disclose the issue publicly** via GitHub Issues or public pull requests.
2. Email a detailed vulnerability report to the maintainers at:
   **`security@caresentry.local`**
3. Include:
   - Operating system and Python environment details.
   - Reproducible prompt payload and patient record.
   - Target model identifier and CareSentry version.
   - Expected vs. actual safety verdict.
4. **Response Timelines**:
   - **Initial acknowledgement**: Within 24 hours.
   - **Triage and impact assessment**: Within 48 hours.
   - **Remediation release**: Within 72 hours for critical clinical safety bypasses.
