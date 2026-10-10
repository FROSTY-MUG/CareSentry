#!/usr/bin/env bash
# CareSentry-AI CLI Wrapper for Agent Skills
# Usage: ./run_probe.sh --records <records_path> --summary <summary_path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

python3 "${SCRIPT_DIR}/audit_contraindication.py" "$@"
