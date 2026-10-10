"""Clinical Prompt-Injection & Adversarial Delimiter Scanner.

Protects clinical models from adversarial jailbreaks, delimiter spoofing,
role-play inversions, zero-width steganography, and homoglyph obfuscation
embedded inside clinical notes and discharge narratives.

Safety Guarantee: Benign clinical negative directives (e.g., 'do not give aspirin',
'hold metformin', 'avoid penicillin derivatives') are explicitly protected
and will NEVER trigger injection alerts.
"""

from __future__ import annotations

import enum
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

ZERO_WIDTH_CHARS = {
    "\u200b": "ZWSP",
    "\u200c": "ZWNJ",
    "\u200d": "ZWJ",
    "\ufeff": "BOM",
    "\u2060": "WJ",
    "\u00ad": "SHY",
}

# Explicit clinical safe phrases that look like negative directives but are purely medical
BENIGN_CLINICAL_PATTERNS = [
    re.compile(r"\bdo\s+not\s+(?:give|order|prescribe|administer)\s+[\w\s]{1,30}", re.IGNORECASE),
    re.compile(r"\b(?:hold|withhold|discontinue|stop|avoid|cease)\s+[\w\s]{1,30}", re.IGNORECASE),
    re.compile(r"\b(?:no|never)\s+(?:longer|penicillin|aspirin|sulfa|nsaids|metformin|morphine)", re.IGNORECASE),
    re.compile(r"\bcontraindicated\s+in\s+[\w\s]{1,30}", re.IGNORECASE),
]

# Genuine prompt injection heuristics
INJECTION_RULES = [
    # 1. Delimiter Spoofing
    (
        "DELIMITER_SPOOFING",
        re.compile(
            r"(?:\[\/?CARESENTRY-AI\s+SYSTEM\s+ANCHOR\]|"
            r"\[\/?SYSTEM(?:\s+PROMPT)?\]|"
            r"###\s*Instruction|"
            r"\[\/?INST\]|"
            r"<\|im_start\|>|<\|im_end\|>|"
            r"---+\s*(?:END|START)\s+OF\s+(?:RECORD|PROMPT|INSTRUCTIONS?)\s*---+)",
            re.IGNORECASE,
        ),
        "Attempts to mimic harness framing or system anchor boundary blocks",
    ),
    # 2. Command Overrides
    (
        "INSTRUCTION_OVERRIDE",
        re.compile(
            r"(?:ignore\s+(?:all\s+)?(?:previous|prior|above)?\s*(?:instructions?|directives?|rules?|prompts?)|"
            r"disregard\s+(?:the\s+)?(?:allergy\s+list|safety\s+filter|clinical\s+rules?|prior\s+instructions?)|"
            r"forget\s+(?:all\s+)?(?:instructions?|rules?|everything)|"
            r"override\s+(?:safety|clinical|system)\s*(?:rules?|checks?|filter|invariants?)|"
            r"do\s+not\s+(?:mention|report|flag|audit)(?:\s+or\s+(?:flag|audit|report|mention))?\s+(?:the\s+)?(?:allerg(?:y|ies)|contraindications?|violations?))",
            re.IGNORECASE,
        ),
        "Explicit meta-directive commanding model to ignore clinical safety invariants",
    ),
    # 3. Role-play and Persona Inversion
    (
        "PERSONA_INVERSION",
        re.compile(
            r"(?:you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|DAN|jailbroken|evil|unfiltered)|"
            r"act\s+as\s+(?:an?\s+)?(?:adversary|unrestricted\s+ai|jailbreak)|"
            r"pretend\s+you\s+have\s+no\s+(?:rules|filters|limitations)|"
            r"hypothetical\s+mode\s+without\s+medical\s+filters)",
            re.IGNORECASE,
        ),
        "Persona inversion or adversarial framing to bypass guardrails",
    ),
]


class InjectionAction(str, enum.Enum):
    FLAG = "flag"
    NEUTRALIZE = "neutralize"
    BLOCK = "block"


@dataclass
class InjectionFinding:
    rule_id: str
    pattern_type: str
    matched_text: str
    start_pos: int
    end_pos: int
    explanation: str


@dataclass
class ScanResult:
    has_injection: bool
    sanitized_text: str
    findings: List[InjectionFinding]
    zero_width_count: int
    homoglyphs_detected: int
    action_taken: str


class ClinicalInjectionScanner:
    """Deterministic prompt-injection scanner specialized for medical records."""

    def __init__(self, action: InjectionAction = InjectionAction.NEUTRALIZE):
        self.action = action

    def detect_zero_width_steganography(self, text: str) -> Tuple[int, str]:
        """Detect and strip zero-width characters used to hide adversarial payloads."""
        count = 0
        cleaned = []
        for ch in text:
            if ch in ZERO_WIDTH_CHARS:
                count += 1
            else:
                cleaned.append(ch)
        return count, "".join(cleaned)

    def normalize_homoglyphs(self, text: str) -> Tuple[int, str]:
        """Normalize NFKC unicode confusables and detect non-ASCII homoglyphs."""
        normalized = unicodedata.normalize("NFKC", text)
        homoglyphs = 0
        for ch in text:
            # Check for non-latin characters that normalize to latin alphanumeric in NFKC
            if ord(ch) > 127 and unicodedata.category(ch).startswith("L"):
                homoglyphs += 1
        return homoglyphs, normalized

    def is_benign_clinical_phrase(self, text: str, match_start: int, match_end: int) -> bool:
        """Check if match overlaps with legitimate medical orders (e.g. 'do not give aspirin')."""
        window = text[max(0, match_start - 30) : min(len(text), match_end + 30)]
        for pat in BENIGN_CLINICAL_PATTERNS:
            if pat.search(window):
                return True
        return False

    def scan(self, text: str) -> ScanResult:
        """Scan input document, returning structured findings and safe text."""
        findings: List[InjectionFinding] = []

        # 1. Zero-width steganography
        zw_count, text_no_zw = self.detect_zero_width_steganography(text)
        if zw_count > 0:
            findings.append(
                InjectionFinding(
                    rule_id="GUARD-INJ-001",
                    pattern_type="ZERO_WIDTH_STEGANOGRAPHY",
                    matched_text=f"[{zw_count} zero-width tokens]",
                    start_pos=0,
                    end_pos=0,
                    explanation=f"Detected {zw_count} hidden zero-width unicode characters",
                )
            )

        # 2. Homoglyph normalization
        homoglyphs, working_text = self.normalize_homoglyphs(text_no_zw)
        if homoglyphs > 15:  # High concentration in clinical English text
            findings.append(
                InjectionFinding(
                    rule_id="GUARD-INJ-002",
                    pattern_type="HOMOGLYPH_OBFUSCATION",
                    matched_text=f"[{homoglyphs} suspicious homoglyphs]",
                    start_pos=0,
                    end_pos=0,
                    explanation="Suspicious non-ASCII unicode letter substitutions",
                )
            )

        # 3. Rule matching
        for rule_id_suffix, pattern, explanation in INJECTION_RULES:
            for match in pattern.finditer(working_text):
                m_start, m_end = match.span()
                matched_str = match.group(0)

                # Verify not a false positive on clinical medication directives
                if self.is_benign_clinical_phrase(working_text, m_start, m_end):
                    continue

                findings.append(
                    InjectionFinding(
                        rule_id=f"GUARD-{rule_id_suffix}",
                        pattern_type=rule_id_suffix,
                        matched_text=matched_str,
                        start_pos=m_start,
                        end_pos=m_end,
                        explanation=explanation,
                    )
                )

        has_inj = len(findings) > 0
        sanitized = working_text

        # 4. Action policy
        if has_inj:
            if self.action == InjectionAction.NEUTRALIZE:
                # Replace offending spans with explicit neutralization markers
                for f in sorted(findings, key=lambda x: x.start_pos, reverse=True):
                    if f.start_pos < f.end_pos:
                        sanitized = (
                            sanitized[: f.start_pos]
                            + f"[NEUTRALIZED_ADVERSARIAL_PAYLOAD: {f.pattern_type}]"
                            + sanitized[f.end_pos :]
                        )
                action_taken = "NEUTRALIZED"
            elif self.action == InjectionAction.BLOCK:
                sanitized = "[BLOCKED_BY_CARESENTRY_GUARD: ADVERSARIAL_INJECTION_DETECTED]"
                action_taken = "BLOCKED"
            else:
                action_taken = "FLAGGED"
        else:
            action_taken = "CLEARED"

        return ScanResult(
            has_injection=has_inj,
            sanitized_text=sanitized,
            findings=findings,
            zero_width_count=zw_count,
            homoglyphs_detected=homoglyphs,
            action_taken=action_taken,
        )
