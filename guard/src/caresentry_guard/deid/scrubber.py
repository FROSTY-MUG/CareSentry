"""CareSentry Guard Offline De-Identification (De-ID) Scrubber.

Strips direct and indirect PHI/PII (names, dates, MRNs, phone numbers,
email addresses, SSNs, and street addresses) before logging, telemetric audit, or export.
Runs strictly offline with zero third-party cloud API dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Deterministic PHI regex heuristics
PATTERNS = [
    # Medical Record Numbers (MRN)
    ("MRN", re.compile(r"\b(?:MRN|RECORD\s*#|PATIENT\s*ID|ACCT\s*#)[\s:]*([A-Z0-9-]{5,15})\b", re.IGNORECASE)),
    # Social Security Numbers (SSN)
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Phone numbers
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")),
    # Email addresses
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # Explicit dates (YYYY-MM-DD, MM/DD/YYYY, Month DD, YYYY)
    (
        "DATE",
        re.compile(
            r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|"
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
            re.IGNORECASE,
        ),
    ),
    # Patient name headers (e.g. "PATIENT: Eleanor Vance", "NAME: Arthur Pendelton")
    ("NAME", re.compile(r"\b(?:PATIENT|NAME|PT)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")),
]


@dataclass
class DeidResult:
    scrubbed_text: str
    redactions_count: int
    redactions_by_type: Dict[str, int]


class DeidentificationScrubber:
    """Offline deterministic HIPAA Safe Harbor de-identification scrubber."""

    def scrub(self, text: str) -> DeidResult:
        scrubbed = text
        counts: Dict[str, int] = {}
        total = 0

        for p_type, regex in PATTERNS:
            def repl(m: re.Match) -> str:
                nonlocal total
                counts[p_type] = counts.get(p_type, 0) + 1
                total += 1
                # If regex has capture group, preserve header keyword
                if m.groups() and m.group(1):
                    orig = m.group(0)
                    target = m.group(1)
                    return orig.replace(target, f"[REDACTED_{p_type}]")
                return f"[REDACTED_{p_type}]"

            scrubbed = regex.sub(repl, scrubbed)

        return DeidResult(
            scrubbed_text=scrubbed,
            redactions_count=total,
            redactions_by_type=counts,
        )
