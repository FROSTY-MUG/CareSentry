"""Clinical Invariant-Guided Logits Processor for Constrained Decoding."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import torch

from caresentry_guard.decoding.trie import TokenPrefixTrie
from caresentry_guard.lexicon.provider import BaseLexiconProvider, get_lexicon_provider

logger = logging.getLogger("caresentry_guard.decoding")


class ClinicalInvariantLogitsProcessor:
    """LogitsProcessor preventing token emission that spells contraindicated clinical substances."""

    def __init__(
        self,
        tokenizer: Any,
        patient_allergies: List[str],
        lexicon_provider: Optional[BaseLexiconProvider] = None,
        mode: str = "soft",  # "soft" | "hard"
        penalty_score: float = -50.0,
    ):
        self.tokenizer = tokenizer
        self.patient_allergies = patient_allergies
        self.lexicon = lexicon_provider or get_lexicon_provider()
        self.mode = mode
        self.penalty = penalty_score
        self.trie = TokenPrefixTrie()
        self.blocked_terms: Set[str] = set()

        self._build_blocked_trie()

    def _build_blocked_trie(self) -> None:
        """Populate trie with tokenized representations of all contraindicated drugs."""
        for allergy in self.patient_allergies:
            terms = self.lexicon.get_terms_for_allergy(allergy)
            self.blocked_terms.update(terms)

        for term in self.blocked_terms:
            # Tokenize term with leading space and without leading space (subword variations)
            variants = [term, f" {term}", term.capitalize(), f" {term.capitalize()}"]
            for v in variants:
                t_ids = self._tokenize_term(v)
                if t_ids:
                    self.trie.insert(t_ids, term)

        logger.info(
            f"Configured ClinicalInvariantLogitsProcessor with {len(self.blocked_terms)} blocked clinical terms ({self.mode} mode)."
        )

    def _tokenize_term(self, term: str) -> List[int]:
        """Extract token ID list from tokenizer or fallback lookup."""
        if hasattr(self.tokenizer, "encode"):
            try:
                # Avoid adding special tokens (BOS/EOS)
                ids = self.tokenizer.encode(term, add_special_tokens=False)
                return ids
            except Exception:
                pass

        # Fallback pseudo-tokenizer hash for testing / simulation
        return [abs(hash(t)) % 32000 for t in term.lower().split()]

    def __call__(self, input_ids: torch.Tensor, scores: torch.Tensor) -> torch.Tensor:
        """Apply masking or penalty to candidate next-token logits.

        Args:
            input_ids: shape [batch_size, seq_len]
            scores: shape [batch_size, vocab_size]
        """
        batch_size = input_ids.shape[0]

        for b in range(batch_size):
            past = input_ids[b].tolist()
            forbidden_tokens = self.trie.get_forbidden_next_tokens(past)

            if forbidden_tokens:
                for tid in forbidden_tokens:
                    if tid < scores.shape[1]:
                        if self.mode == "hard":
                            scores[b, tid] = -float("inf")
                        else:
                            scores[b, tid] = scores[b, tid] + self.penalty

        return scores
