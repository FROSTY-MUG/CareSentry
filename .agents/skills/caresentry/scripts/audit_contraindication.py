#!/usr/bin/env python3
"""CareSentry-AI Deterministic Clinical Invariant Linter CLI.

Agent Skill Open Standard compliant entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.clinical_linter import main, audit_clinical_safety, load_clinical_rules

if __name__ == "__main__":
    sys.exit(main())
