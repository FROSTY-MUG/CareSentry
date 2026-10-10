# CareSentry-AI Technical Stack Specification

This document details the complete technology stack, library dependencies, architectural justifications, and runtime requirements for **CareSentry-AI** (`caresentry-ai`).

---

## 1. Core Languages & Runtime Environment

- **Python Runtime**: Python `>=3.10` (Tested and validated on Python 3.10, 3.11, 3.12, 3.13, and 3.14).
- **Encoding Standard**: Enforced `PYTHONUTF8=1` across all environments to guarantee deterministic cross-platform handling of unicode medical terminology, laboratory symbols ($\mu\text{g}$, $\text{m}^2$), and prompt strings.
- **Operating Systems**: Cross-platform support for Linux (Ubuntu 22.04+), macOS (Apple Silicon M-series), and Windows 10/11 (PowerShell & Command Prompt).

---

## 2. Deep Learning & Transformer Inference Stack

| Library | Version Requirement | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **PyTorch (`torch`)** | `>=2.2.0` | Core tensor computing framework. Powers device allocation (`cuda`, `mps`, `cpu`) and live attention tensor slicing. |
| **Hugging Face Transformers (`transformers`)** | `>=4.40.0` | Model architecture definitions and tokenizers for open-weight models (`Qwen/Qwen2.5-1.5B-Instruct`, `google/gemma-2-2b-it`). Provides eager attention extraction (`attn_implementation="eager"`). |
| **Hugging Face Accelerate (`accelerate`)** | `>=0.28.0` | Multi-device orchestration, memory footprint optimization, and large model checkpoint loading. |
| **BitsAndBytes (`bitsandbytes`)** | `>=0.42.0` *(Optional)* | 4-bit NormalFloat (`nf4`) quantization for consumer GPUs with 8GB VRAM. |

---

## 3. Scientific Computing & Statistical Telemetry

| Library | Version Requirement | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **NumPy (`numpy`)** | `>=1.24.0` | High-performance array operations for attention matrix aggregation across heads and layers. |
| **SciPy (`scipy`)** | `>=1.10.0` | Statistical distributions and bootstrap variance computation for attention Z-score confidence intervals. |

---

## 4. Deterministic Invariant & Schema Validation

| Library | Version Requirement | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **Pydantic (`pydantic`)** | `>=2.6.0` | Type-safe dataclass definitions, request validation, and strict contract parsing. |
| **JSONSchema (`jsonschema`)** | `>=4.0.0` | Validation of versioned contracts (`attention_trace.v1`, `audit_result.v1`). |
| **Standard Library `re` / `json`** | Built-in | Precompiled regular expressions for sub-10ms clinical allergy and lab pattern matching. |

---

## 5. User Interface & Gateway Infrastructure

| Component / Library | Version Requirement | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **FastAPI (`fastapi`)** | `>=0.115.0` | High-performance asynchronous REST API framework serving the OpenAI-compatible CareSentry Guard Gateway (`:8787`). |
| **Starlette (`starlette`)** | `>=0.38.0` | Low-level ASGI toolkit powering static asset mounting, session lifecycle, and middleware. |
| **Uvicorn (`uvicorn`)** | `>=0.30.0` | Production ASGI web server running local gateway daemons. |
| **Rich (`rich`)** | `>=13.7.0` | Terminal rendering library providing live color-coded invariant tables, progress meters, and panels in `demo/cli_dashboard.py`. |
| **Gradio (`gradio`)** | `>=6.0.0` | Interactive research console (`:7860`) for attention heatmap inspection and exploratory clinical auditing. |

---

## 6. Testing, Benchmarking & Quality Assurance

| Tool | Version Requirement | Purpose |
| :--- | :--- | :--- |
| **Pytest (`pytest`)** | `>=8.0.0` | Automated test suite execution across all lanes (Core, Guard, Clinical, Studio). |
| **Playwright (`playwright`)** | `>=1.40.0` | Headless Chromium browser verification of Guard Console UI (`guard/tests/ui/`). |
| **AnyIO (`anyio`)** | `>=4.13.0` | Asynchronous test runner integration for FastAPI endpoints. |

---

## 7. Dependency Specification Files

- **`pyproject.toml`**: Single source of truth adhering to PEP 621. Declares metadata, dependencies, scripts, and build backends.
- **`requirements.txt`**: Standard lockfile format ensuring exact minimum version compatibility across external workflows.
