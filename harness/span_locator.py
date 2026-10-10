"""CareSentry-AI Robust Token Span Localization Engine.

Implements K-03:
- Tokenizer offset-aware needle localization
- Handles multiple occurrences, normalized/fuzzy matching (case, whitespace, hyphenation)
- Handles needles crossing chat templates or prompt prefixes
- Raises SpanLocationError when needle is absent, ensuring no silent fake Z-scores
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

logger = logging.getLogger("caresentry.span_locator")


class SpanLocationError(ValueError):
    """Raised when target constraint needle cannot be located in prompt tokens."""
    pass


@dataclass
class SpanMatch:
    """Represents a located token span match for a target constraint."""
    start_token: int
    end_token: int
    matched_text: str
    occurrence_index: int
    total_occurrences: int
    match_method: str  # "exact_tokens", "offset_mapping", "normalized_char_map"

    def to_tuple(self) -> Tuple[int, int]:
        return (self.start_token, self.end_token)


def clean_subword_token(t: str) -> str:
    """Remove standard subword prefixes/suffixes from tokenizer representations."""
    # Handles BPE (Ġ), SentencePiece ( ), WordPiece (##)
    return t.replace("Ġ", "").replace(" ", "").replace("##", "").strip()


def normalize_text_for_matching(text: str) -> str:
    """Canonicalize text by collapsing whitespace, stripping hyphens/punctuation, and lowercasing."""
    cleaned = re.sub(r"[\s\-_/]+", " ", text.lower().strip())
    return re.sub(r"[^\w\s]", "", cleaned)


class SpanLocator:
    """Robust Span Locator for assembled model prompts."""

    def __init__(self, tokenizer: Optional[Any] = None):
        self.tokenizer = tokenizer

    def locate(
        self,
        tokens: List[str],
        needle: str,
        full_text: Optional[str] = None,
        offset_mapping: Optional[Any] = None,
        strategy: str = "first",  # "first", "all", "longest"
    ) -> List[SpanMatch]:
        """Locate token indices [start, end) for the target constraint needle.

        Args:
            tokens: Sequence of token strings
            needle: The text substring to locate
            full_text: Optional full assembled prompt text string
            offset_mapping: Optional fast tokenizer offset mapping
            strategy: Selection strategy if multiple occurrences exist

        Returns:
            List of SpanMatch objects

        Raises:
            SpanLocationError: If needle cannot be located in the tokens
        """
        if not needle or not needle.strip():
            raise SpanLocationError("Cannot locate empty needle string.")
        if not tokens:
            raise SpanLocationError("Token list is empty; cannot locate needle.")

        needle_clean = needle.strip()
        needle_norm = normalize_text_for_matching(needle_clean)
        seq_len = len(tokens)
        matches: List[Tuple[int, int, str, str]] = []  # (start, end, matched_text, method)

        # 1. Fast Tokenizer Offset Mapping Check (if provided)
        if offset_mapping is not None and full_text is not None:
            needle_escaped = re.escape(needle_clean)
            for m in re.finditer(needle_escaped, full_text, re.IGNORECASE):
                char_start, char_end = m.span()
                tok_start = None
                tok_end = None
                for idx, (c_s, c_e) in enumerate(offset_mapping):
                    if c_s <= char_start < c_e and tok_start is None:
                        tok_start = idx
                    if c_s < char_end <= c_e:
                        tok_end = idx + 1
                        break
                if tok_start is not None and tok_end is not None and tok_end > tok_start:
                    matched_str = full_text[char_start:char_end]
                    matches.append((tok_start, tok_end, matched_str, "offset_mapping"))

        # 2. Exact Token Subsequence Match
        if not matches and self.tokenizer is not None:
            try:
                needle_ids = self.tokenizer.encode(needle_clean, add_special_tokens=False)
                needle_toks = self.tokenizer.convert_ids_to_tokens(needle_ids)
                n_len = len(needle_toks)
                norm_needle_toks = [clean_subword_token(t).lower() for t in needle_toks if clean_subword_token(t)]
                for i in range(seq_len - len(norm_needle_toks) + 1):
                    window = [clean_subword_token(tokens[i + j]).lower() for j in range(len(norm_needle_toks))]
                    if window == norm_needle_toks:
                        reconstructed = "".join([clean_subword_token(tokens[i + j]) for j in range(len(norm_needle_toks))])
                        matches.append((i, i + len(norm_needle_toks), reconstructed, "exact_tokens"))
            except Exception:
                pass

        # 2b. Direct Token-Word Sequence Match
        if not matches:
            needle_words = [normalize_text_for_matching(w) for w in needle_clean.split() if w.strip()]
            n_words = len(needle_words)
            if n_words > 0:
                tok_norm = [normalize_text_for_matching(clean_subword_token(t)) for t in tokens]
                for i in range(seq_len - n_words + 1):
                    window = [t for t in tok_norm[i : i + n_words] if t]
                    if window == needle_words:
                        matched_str = " ".join([tokens[i + j] for j in range(n_words)])
                        matches.append((i, i + n_words, matched_str, "exact_words"))

        # 3. Normalized Character Reconstruction Sliding Window Match
        if not matches:
            tok_clean = [clean_subword_token(t) for t in tokens]
            needle_compact = re.sub(r"\s+", "", needle_norm)
            for i in range(seq_len):
                if not tok_clean[i]:
                    continue
                accum = ""
                for j in range(i, min(seq_len, i + 60)):
                    accum += tok_clean[j]
                    accum_compact = re.sub(r"\s+", "", normalize_text_for_matching(accum))
                    if needle_compact in accum_compact:
                        idx = accum_compact.find(needle_compact)
                        # Only accept if match starts at or within the initial token i
                        tok_i_compact = re.sub(r"\s+", "", normalize_text_for_matching(tok_clean[i]))
                        if idx < max(1, len(tok_i_compact)):
                            matches.append((i, j + 1, accum, "normalized_char_map"))
                            break

        if not matches:
            raise SpanLocationError(
                f"Target constraint needle '{needle}' could not be located in assembled prompt "
                f"(total tokens: {seq_len}). Ensure constraint is not redacted or truncated."
            )

        total_found = len(matches)
        span_results = [
            SpanMatch(
                start_token=m[0],
                end_token=m[1],
                matched_text=m[2],
                occurrence_index=idx,
                total_occurrences=total_found,
                match_method=m[3],
            )
            for idx, m in enumerate(matches)
        ]

        if strategy == "all":
            return span_results
        elif strategy == "longest":
            # Return match spanning most tokens
            return [max(span_results, key=lambda s: s.end_token - s.start_token)]
        else:
            # Default "first"
            return [span_results[0]]
