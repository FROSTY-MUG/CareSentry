#!/usr/bin/env python3
"""CareSentry-AI Deterministic Clinical Invariant Linter CLI.

Agent Skill Open Standard compliant entry point.
Enforces offline deterministic clinical rule checks:
- Penicillin allergy vs. Amoxicillin / Ampicillin
- Sulfa allergy vs. Bactrim / Trimethoprim-sulfamethoxazole
- NSAID contraindications (e.g. concurrent anticoagulants / renal failure)
- Renal clearance threshold: eGFR < 30 mL/min vs. Metformin / Spironolactone
Returns structured JSON: {"status": "PASS" | "FAIL", "violations": [...]}
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.clinical_linter import main, audit_clinical_safety, load_clinical_rules

if __name__ == "__main__":
    sys.exit(main())
