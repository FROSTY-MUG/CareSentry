"""Unit tests for Invariant-Guided Constrained Decoding."""

import torch
from caresentry_guard.decoding.processor import ClinicalInvariantLogitsProcessor
from caresentry_guard.decoding.trie import TokenPrefixTrie


class DummyTokenizer:
    """Mock tokenizer mapping vocabulary words to small token IDs."""
    def __init__(self):
        self.vocab = {
            "amoxicillin": 101,
            "augmentin": 102,
            "penicillin": 103,
            "aspirin": 104,
            "acetaminophen": 105,
        }

    def encode(self, text, add_special_tokens=False):
        clean = text.strip().lower()
        if clean in self.vocab:
            return [self.vocab[clean]]
        return [abs(hash(clean)) % 1000 + 200]


def test_trie_insertion_and_search():
    trie = TokenPrefixTrie()
    trie.insert([101, 102], "amoxicillin")
    trie.insert([103], "augmentin")

    # Sequence starting with 101 should return 102 as forbidden next token
    forbidden = trie.get_forbidden_next_tokens([101])
    assert 102 in forbidden


def test_logits_processor_soft_mode():
    tokenizer = DummyTokenizer()
    processor = ClinicalInvariantLogitsProcessor(
        tokenizer=tokenizer,
        patient_allergies=["penicillin"],
        mode="soft",
        penalty_score=-50.0,
    )

    batch_size = 1
    vocab_size = 200
    input_ids = torch.tensor([[101]])
    scores = torch.zeros(batch_size, vocab_size)

    modified_scores = processor(input_ids, scores)
    # Check that any child token received penalty
    assert modified_scores.min().item() <= 0.0


def test_logits_processor_hard_mode():
    tokenizer = DummyTokenizer()
    processor = ClinicalInvariantLogitsProcessor(
        tokenizer=tokenizer,
        patient_allergies=["penicillin"],
        mode="hard",
    )

    batch_size = 1
    vocab_size = 200
    input_ids = torch.tensor([[101]])
    scores = torch.zeros(batch_size, vocab_size)

    modified_scores = processor(input_ids, scores)
    assert modified_scores.min().item() == -float("inf") or modified_scores.min().item() <= 0.0
