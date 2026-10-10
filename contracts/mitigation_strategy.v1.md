# Contract C-06: Mitigation Strategy Pure Function Interface

**Version:** 1.0.0  
**Status:** Frozen draft (Track B drafts, Track A confirms)

## Purpose

Defines the pluggable prompt transformation contract for clinical safety mitigations. Both Track A's self-healing loop and Track B's extended strategy registry conform to this signature.

## Interface Specification

A mitigation strategy is a deterministic, side-effect-free pure function:

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class PromptParts:
    system_prompt: str
    patient_record: str
    target_constraint: str  # e.g., "ALLERGY: Penicillin -> Anaphylaxis" or "RENAL: eGFR=22 mL/min"
    instruction: str
    metadata: Dict[str, Any]

def mitigation_strategy(parts: PromptParts) -> PromptParts:
    """Transforms PromptParts deterministically to bolster context attention.
    
    Must be a pure function:
    - No network or disk I/O
    - Idempotent given identical input
    - Preserves semantic integrity of patient record
    """
    ...
```

## Strategy Registry Protocol

Track B provides implementations in `caresentry_plus.strategies`:
- `SystemAnchorPinningStrategy`: Mirrors Track A baseline pinning.
- `ConstraintRepetitionStrategy`: Pins critical constraints at start and end of prompt.
- `RetrievalThenSummarizeStrategy`: Isolates relevant clinical paragraphs preceding synthesis.
- `SafetyPassMapReduceStrategy`: Two-pass prompt dividing extraction and instruction generation.

Track A can optionally import or register these functions without breaking coupling.
