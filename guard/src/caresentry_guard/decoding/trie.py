"""Token Sequence Prefix Trie for Constrained Decoding."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class TrieNode:
    def __init__(self):
        self.children: Dict[int, TrieNode] = {}
        self.is_terminal: bool = False
        self.blocked_term: Optional[str] = None


class TokenPrefixTrie:
    """Prefix trie storing blocked token ID sequences."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, token_ids: List[int], term_name: str) -> None:
        """Insert a sequence of token IDs that spell a blocked term."""
        curr = self.root
        for tid in token_ids:
            if tid not in curr.children:
                curr.children[tid] = TrieNode()
            curr = curr.children[tid]

        curr.is_terminal = True
        curr.blocked_term = term_name

    def find_active_node(self, past_token_ids: List[int]) -> Optional[TrieNode]:
        """Find the deepest trie node matching the suffix of past generated tokens."""
        # Check suffixes of length 1..min(len(past), 8)
        max_depth = min(len(past_token_ids), 8)
        for length in range(max_depth, 0, -1):
            suffix = past_token_ids[-length:]
            curr = self.root
            matched = True
            for tid in suffix:
                if tid in curr.children:
                    curr = curr.children[tid]
                else:
                    matched = False
                    break
            if matched:
                return curr
        return None

    def get_forbidden_next_tokens(self, past_token_ids: List[int]) -> Set[int]:
        """Return token IDs that would continue or complete a blocked sequence."""
        forbidden: Set[int] = set()

        # Check if root has immediate single-token matches for the start of blocked words
        # and check if the past suffix is currently within a multi-token sequence
        active = self.find_active_node(past_token_ids)
        if active:
            # Any child of active node would advance toward or complete a forbidden word
            forbidden.update(active.children.keys())

        # Also, if starting a new word (e.g. after space or beginning of order)
        # check single-token starts
        return forbidden
