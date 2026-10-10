# CareSentry-AI Model Compatibility Matrix (F-09)

Empirical compatibility test results of open-weight LLMs with eager-attention probing.

| Model ID | Tier | Params | License | Attn Type | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `Qwen/Qwen2.5-1.5B-Instruct` | Edge / demo | 1.54B | Apache-2.0 | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `Qwen/Qwen2.5-0.5B-Instruct` | Edge / demo | 0.49B | Apache-2.0 | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `microsoft/Phi-4-mini-instruct` | Edge / demo | 3.8B | MIT | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `Qwen/Qwen2.5-7B-Instruct` | Mid | 7.61B | Apache-2.0 | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `google/gemma-2-9b-it` | Mid | 9.24B | Gemma Terms of Use | `hybrid_sliding_global` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `mistralai/Mistral-7B-Instruct-v0.3` | Mid | 7.25B | Apache-2.0 | `sliding_window` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `aaditya/Llama3-OpenBioLLM-8B` | Medical comparison | 8.03B | Meta Llama 3 Community | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `epfl-llm/meditron-7b` | Medical comparison | 6.74B | Llama-2 Community | `dense` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `meta-llama/Llama-3.1-8B-Instruct` | Long context | 8.03B | Llama 3.1 Community | `dense_rope_scaled` | ✅ PASS | Runner tokenization and eager-attention extraction verified. |
| `deepseek-ai/DeepSeek-V2.5` | Linter-only (no attention extraction) | 236B (21B active) | DeepSeek License | `mla_moe` | ⏸️ SKIP | Multi-head Latent Attention (MLA) architecture too large for local attention tensor extraction. Covered by invariant rule gate only. |
