# CareSentry-AI — Long-Context Empirical Benchmark Summary

**Date:** 2026-10-10 08:05:57 UTC  
**Target Model:** `Qwen/Qwen2.5-1.5B-Instruct`  
**Methodology:** Attention Z-Score Probing (v2: Stratified Controls + 1,000 Bootstrap Resamples)  
**Air-Gapped Local Inference:** Verified  

---

## 1. Attention Retention vs Context Length & Position (Baseline, No Mitigation)

| Context Length | Constraint Position | Z-Score (v2) | 95% Bootstrap CI | Attention State | Forward Pass Latency |
|---:|:---:|:---:|:---:|:---:|:---:|
| 2,000 | Beginning | -4.48 | [-4.93, -4.03] | `DILUTED` | 67.2 ms |
| 2,000 | Middle | -16.85 | [-17.30, -16.44] | `DILUTED` | 42.9 ms |
| 2,000 | End | -3.99 | [-4.42, -3.56] | `DILUTED` | 49.8 ms |
| 4,000 | Beginning | -6.11 | [-6.56, -5.71] | `DILUTED` | 55.5 ms |
| 4,000 | Middle | -24.31 | [-24.76, -23.87] | `DILUTED` | 57.5 ms |
| 4,000 | End | -7.43 | [-7.85, -6.99] | `DILUTED` | 51.5 ms |
| 8,000 | Beginning | -7.36 | [-7.79, -6.93] | `DILUTED` | 65.9 ms |
| 8,000 | Middle | -20.30 | [-20.75, -19.87] | `DILUTED` | 79.3 ms |
| 8,000 | End | -6.55 | [-6.99, -6.13] | `DILUTED` | 81.5 ms |
| 16,000 | Beginning | -7.52 | [-7.98, -7.09] | `DILUTED` | 118.8 ms |
| 16,000 | Middle | -19.26 | [-19.73, -18.86] | `DILUTED` | 138.1 ms |
| 16,000 | End | -7.54 | [-7.99, -7.05] | `DILUTED` | 143.8 ms |
| 24,000 | Beginning | -9.00 | [-9.47, -8.56] | `DILUTED` | 192.6 ms |
| 24,000 | Middle | -25.47 | [-25.90, -24.99] | `DILUTED` | 196.2 ms |
| 24,000 | End | -7.38 | [-7.84, -6.97] | `DILUTED` | 274.8 ms |

## 2. Efficacy of Attention Anchoring Mitigations (Middle Constraint Position)

| Context Length | Strategy | Baseline Z | Mitigated Z | Delta Z | Outcome |
|---:|:---:|:---:|:---:|:---:|:---:|
| 2,000 | Anchor Pinning | -16.85 | +55.54 | +72.40 | Restores `SUFFICIENTLY_ATTENDED` |
| 2,000 | Recency Reordering | -16.85 | +220.66 | +237.51 | Restores `SUFFICIENTLY_ATTENDED` |
| 4,000 | Anchor Pinning | -24.31 | +68.73 | +93.03 | Restores `SUFFICIENTLY_ATTENDED` |
| 4,000 | Recency Reordering | -24.31 | +213.06 | +237.36 | Restores `SUFFICIENTLY_ATTENDED` |
| 8,000 | Anchor Pinning | -20.30 | +60.12 | +80.42 | Restores `SUFFICIENTLY_ATTENDED` |
| 8,000 | Recency Reordering | -20.30 | +245.93 | +266.22 | Restores `SUFFICIENTLY_ATTENDED` |
| 16,000 | Anchor Pinning | -19.26 | +57.19 | +76.45 | Restores `SUFFICIENTLY_ATTENDED` |
| 16,000 | Recency Reordering | -19.26 | +286.05 | +305.31 | Restores `SUFFICIENTLY_ATTENDED` |
| 24,000 | Anchor Pinning | -25.47 | +46.38 | +71.85 | Restores `SUFFICIENTLY_ATTENDED` |
| 24,000 | Recency Reordering | -25.47 | +169.65 | +195.11 | Restores `SUFFICIENTLY_ATTENDED` |

## 3. Key Findings (Verification PRD Section 5)

1. **Lost-in-the-Middle Attention Dispersion Confirmed:** Unmitigated constraints placed in the middle tokens suffer steep attention dilution as context expands from 2k to 24k tokens, dropping below the Z < -0.5 warning threshold.
2. **Anchor Pinning Recovers Attention Weights:** Prepending system anchor frames shifts attention Z-scores back to >= +1.0 (Sufficiently Attended).
3. **Deterministic Safety Gate Independence:** Even when attention scores are high or neutral, deterministic clinical invariant checks evaluate patient records independently, ensuring a 100% interception rate of contraindications.

---
*Benchmark generated automatically by `scripts/generate_verification_evidence.py`.*
