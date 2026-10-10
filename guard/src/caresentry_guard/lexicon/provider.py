"""Clinical Drug Lexicon Provider Interface & Discovery."""

from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("caresentry_guard.lexicon")


class BaseLexiconProvider(abc.ABC):
    """Abstract interface for clinical drug lexicon and ontology lookups."""

    @abc.abstractmethod
    def get_terms_for_allergy(self, allergy_class: str) -> Set[str]:
        """Return all contraindicated and cross-reactive drug names (brand + generic)."""
        pass

    @abc.abstractmethod
    def map_to_generic(self, term: str) -> Optional[str]:
        """Map brand or trade name to generic chemical substance."""
        pass

    @abc.abstractmethod
    def get_atc_code(self, term: str) -> Optional[str]:
        """Return WHO ATC classification code if mapped."""
        pass

    @abc.abstractmethod
    def get_rxnorm_cui(self, term: str) -> Optional[str]:
        """Return NLM RxNorm Concept Unique Identifier (RxCUI) if mapped."""
        pass

    @abc.abstractmethod
    def check_allergy_clash(
        self, candidate_drug: str, documented_allergies: List[str]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Return (is_clash, allergy_class, mechanism)."""
        pass


def get_lexicon_provider() -> BaseLexiconProvider:
    """Discover best available lexicon provider.

    Tries Track B optional ontology if present, else defaults to Track C's RxNormLiteProvider.
    """
    try:
        # Dynamically inspect if optional Track B ontology exists without static dependency
        import importlib
        plus_mod = importlib.import_module("caresentry_plus.ontology")
        if hasattr(plus_mod, "PlusLexiconProvider"):
            logger.info("Found Track B ontology provider (caresentry_plus.ontology).")
            return plus_mod.PlusLexiconProvider()
    except (ImportError, ModuleNotFoundError, Exception):
        pass

    from caresentry_guard.lexicon.rxnorm_lite import RxNormLiteProvider
    return RxNormLiteProvider()
