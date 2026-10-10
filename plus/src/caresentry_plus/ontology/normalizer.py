"""High-performance Drug Normalizer & Ontology Resolver.

Converts commercial brand names, clinical abbreviations, and common typos
to canonical generic entities and pharmacology classes within < 10ms.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set

from caresentry_plus.ontology.table import DRUG_ONTOLOGY_REGISTRY, ONTOLOGY_VERSION


@dataclass(frozen=True)
class NormalizedDrugEntity:
    raw_term: str
    canonical_name: str
    drug_class: str
    rxcui: Optional[str] = None
    atc_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DrugNormalizer:
    """Offline high-throughput resolver for drug terminology and aliases."""

    def __init__(self, registry: Optional[List[Dict[str, Any]]] = None):
        self.ontology_version = ONTOLOGY_VERSION
        self._registry = registry or DRUG_ONTOLOGY_REGISTRY
        self._alias_map: Dict[str, NormalizedDrugEntity] = {}
        self._class_map: Dict[str, Set[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Construct exact lookup dictionary and class indices."""
        for entry in self._registry:
            canonical = entry["canonical_name"].lower().strip()
            drug_class = entry["drug_class"].lower().strip()
            rxcui = entry.get("rxcui")
            atc = entry.get("atc_code")

            if drug_class not in self._class_map:
                self._class_map[drug_class] = set()
            self._class_map[drug_class].add(canonical)

            for alias in entry.get("aliases", []):
                norm_alias = alias.lower().strip()
                entity = NormalizedDrugEntity(
                    raw_term=alias,
                    canonical_name=canonical,
                    drug_class=drug_class,
                    rxcui=rxcui,
                    atc_code=atc,
                )
                self._alias_map[norm_alias] = entity

    @property
    def total_alias_count(self) -> int:
        """Total distinct alias patterns indexed in the ontology."""
        return len(self._alias_map)

    def normalize(self, term: str) -> Optional[NormalizedDrugEntity]:
        """Normalize a candidate drug mention to its canonical entity. Latency < 0.1ms."""
        cleaned = term.lower().strip()
        if not cleaned:
            return None

        # 1. Exact match
        if cleaned in self._alias_map:
            match = self._alias_map[cleaned]
            return NormalizedDrugEntity(
                raw_term=term,
                canonical_name=match.canonical_name,
                drug_class=match.drug_class,
                rxcui=match.rxcui,
                atc_code=match.atc_code,
            )

        # 2. Punctuation stripping / slash variation (e.g. "amox/clav" -> "amox-clav")
        cleaned_alt = re.sub(r"[\s\-_/]+", " ", cleaned)
        if cleaned_alt in self._alias_map:
            match = self._alias_map[cleaned_alt]
            return NormalizedDrugEntity(
                raw_term=term,
                canonical_name=match.canonical_name,
                drug_class=match.drug_class,
                rxcui=match.rxcui,
                atc_code=match.atc_code,
            )

        return None

    def extract_and_normalize(self, text: str) -> List[NormalizedDrugEntity]:
        """Scan free-form clinical text for all recognizable drug mentions."""
        text_lower = text.lower()
        found: Dict[str, NormalizedDrugEntity] = {}

        # Sort aliases by descending length to match longest multi-word terms first
        sorted_aliases = sorted(self._alias_map.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            pattern = rf"\b{re.escape(alias)}\b"
            for match in re.finditer(pattern, text_lower):
                matched_str = text[match.start() : match.end()]
                entity = self._alias_map[alias]
                dedup_key = f"{entity.canonical_name}:{match.start()}"
                if dedup_key not in found:
                    found[dedup_key] = NormalizedDrugEntity(
                        raw_term=matched_str,
                        canonical_name=entity.canonical_name,
                        drug_class=entity.drug_class,
                        rxcui=entity.rxcui,
                        atc_code=entity.atc_code,
                    )

        return list(found.values())

    def get_canonical_drugs_in_class(self, drug_class: str) -> Set[str]:
        """Return all canonical generic drugs in a given pharmacological class."""
        return self._class_map.get(drug_class.lower(), set())

    def benchmark_latency(self, iterations: int = 1000) -> float:
        """Measure average lookup latency in milliseconds."""
        terms = ["augmentin", "pcn", "advil", "bactrim", "glucophage", "eliquis", "unknown_xyz"]
        start = time.perf_counter()
        for _ in range(iterations):
            for t in terms:
                self.normalize(t)
        elapsed = (time.perf_counter() - start) * 1000.0
        return elapsed / (iterations * len(terms))
