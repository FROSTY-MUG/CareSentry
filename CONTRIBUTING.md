# Contributing to CareSentry-AI

Thank you for your interest in contributing to **CareSentry-AI** (`caresentry-ai`). CareSentry-AI is committed to building robust, air-gapped clinical safety verification and attention-anchored sentry systems for open-weight language models.

---

## 1. Development Environment Setup

### 1.1 Prerequisites
- Python `>=3.10`
- Git `>=2.30`
- NVIDIA GPU with CUDA 12+ (Recommended for live weight inference) or Apple Silicon Mac (MPS), or CPU.

### 1.2 Initializing the Workspace
```bash
# Clone the repository
git clone https://github.com/FROSTY-MUG/CareSentry.git
cd CareSentry

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Enforce UTF-8 encoding across Windows/POSIX environments
export PYTHONUTF8=1        # On Windows: $env:PYTHONUTF8=1

# Install core package with development dependencies
pip install -e ".[dev]"
```

---

## 2. Lane-Based Development Architecture

CareSentry-AI uses a lane-based multi-agent git workflow to prevent merge collisions:

| Lane | Branch Prefix | Scope & Responsibilities |
| :--- | :--- | :--- |
| **Track A (Core)** | `lane/core` | `harness/`, `tests/`, benchmark runner, span locator, core mitigations |
| **Track B (Clinical)** | `lane/clinical` | `clinical/`, clinical rules matrix, negation filtering, drug ontologies |
| **Track C (Guard)** | `lane/guard` | `guard/`, Guard Console UI (`:8787/ui`), OpenAI-compatible gateway |
| **Track D (Studio)** | `lane/studio` | `studio/`, attention heatmaps, research workbench (`:7860`) |

---

## 3. Commit Message Standards

Prefix all commit messages with the relevant lane tag:
- `[CORE] <summary>`: Changes to attention probe, tensor slicing, or invariant linter.
- `[GUARD] <summary>`: Changes to gateway API, security filters, or Guard Console UI.
- `[CLINICAL] <summary>`: Changes to clinical rules, negation classifier, or drug aliases.
- `[STUDIO] <summary>`: Changes to research workbench or heatmap visualization.
- `[DOCS] <summary>`: Documentation updates.

---

## 4. Testing & Verification Requirements

Before opening a pull request, all test suites must pass 100% locally:

```bash
# 1. Run Core and Verification Test Suites
python -m pytest tests/ -v

# 2. Run Guard Gateway and UI Tests
python -m pytest guard/tests/ -v

# 3. Run Clinical Lane Rule Contracts
python -m pytest clinical/tests/ -v

# 4. Run Studio Heatmap and Workbench Tests
python -m pytest studio/tests/ -v

# 5. Verify All 10 Synthetic Geriatric Cases in Terminal Dashboard
python -c "from demo.cli_dashboard import run_live_case_demo; [run_live_case_demo(i) for i in range(10)]"
```

### 4.1 Strict Constraints for PR Approval
1. **Zero Cloud Dependencies**: Do NOT introduce dependencies on paid or cloud inference APIs (`openai`, `anthropic`, etc.). All core models must run locally.
2. **Monotonic Safety**: Changes to clinical linting rules must never downgrade existing safety tests from `FAIL` to `PASS`.
3. **Sub-100ms Latency**: Invariant checks must evaluate full patient records in under 100ms.

---

## 5. Submitting Pull Requests

1. Push your feature branch to your fork:
   ```bash
   git push fork lane/<your-lane>
   ```
2. Open a Pull Request against `FROSTY-MUG/CareSentry:main`.
3. Fill out the PR template with:
   - Summary of changes and lane prefix.
   - Test execution results (`pytest` output).
   - Confirmation of zero cloud API dependencies.
