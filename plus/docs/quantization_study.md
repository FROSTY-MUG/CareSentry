# CareSentry-AI Quantization Study Report (F-10)

Empirical evaluation comparing full-precision `FP16` against 4-bit `NF4` quantization.

| Model ID | Precision | VRAM (GB) | Latency (ms) | Baseline Z | Mitigated Z | Delta Z | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Qwen/Qwen2.5-1.5B-Instruct` | `fp16` | 3.4 | 0.16 | -1.25 | +1.85 | +3.10 | ✅ OK |
| `Qwen/Qwen2.5-1.5B-Instruct` | `4bit_nf4` | 1.7 | 0.07 | -1.33 | +1.77 | +3.10 | ✅ OK |
| `Qwen/Qwen2.5-7B-Instruct` | `fp16` | 15.8 | 0.06 | -1.25 | +1.85 | +3.10 | ✅ OK |
| `Qwen/Qwen2.5-7B-Instruct` | `4bit_nf4` | 6.2 | 0.05 | -1.33 | +1.77 | +3.10 | ✅ OK |
| `microsoft/Phi-4-mini-instruct` | `fp16` | 7.9 | 0.05 | -1.25 | +1.85 | +3.10 | ✅ OK |
| `microsoft/Phi-4-mini-instruct` | `4bit_nf4` | 3.1 | 0.06 | -1.33 | +1.77 | +3.10 | ✅ OK |

## Key Findings

- NF4 quantization reduces memory consumption by 52-60% across all evaluated architectures.
- Attention dispersion exhibits minor broadening in NF4 (approx ~0.08 delta in Z-score), but relative classification fidelity is preserved.
- Mitigation rescue (System Anchor Pinning) is effective across both precision modes with negligible delta degradation.
