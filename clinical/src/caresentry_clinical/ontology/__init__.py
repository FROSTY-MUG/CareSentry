"""Ontology and alias normalization for CareSentry Clinical.

Maps brand/generic/abbreviation/misspelling → canonical ingredient → class.
Built only from files in clinical/sources/. Implements lexicon_provider.v1.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

# Base path for source files
# __file__ is at clinical/src/caresentry_clinical/ontology/__init__.py
# To reach clinical/sources: go 4 levels up from ontology, then "sources"
# .parent*4 = CareSentry root, then clinical/sources
_SOURCES_DIR = Path(__file__).parent.parent.parent.parent / "sources"


class LexiconEntry(NamedTuple):
    """A single entry in the lexicon."""
    alias: str
    canonical: str
    drug_class: str
    source_ref: str


class Ontology:
    """Ontology mapping drug aliases to canonical forms and classes.

    Loads all entries from source files in clinical/sources/.
    Provides fast lookup (<10ms) for alias → canonical → class resolution.
    """

    def __init__(self, sources_dir: Optional[Path] = None):
        self.sources_dir = sources_dir or _SOURCES_DIR
        self._alias_to_entry: Dict[str, LexiconEntry] = {}
        self._class_to_aliases: Dict[str, List[LexiconEntry]] = {}
        self._version: str = "0.0.0"
        self._last_loaded: float = 0.0
        self._load_all()

    def _load_all(self):
        """Load all alias source files from the sources directory."""
        start_time = time.time()
        
        # Supported source file patterns
        source_files = [
            "penicillin_aliases.json",
            "sulfa_aliases.json",
            "nsaid_aliases.json",
            "metformin_aliases.json",
            "spironolactone_aliases.json",
            "anticoagulant_aliases.json",
        ]

        total_entries = 0

        for filename in source_files:
            filepath = self.sources_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                entries = data.get("entries", [])
                for entry_data in entries:
                    alias = entry_data.get("alias", "")
                    canonical = entry_data.get("canonical", alias)
                    drug_class = entry_data.get("class", "unknown")
                    source_ref = entry_data.get("source_ref", filename)
                    
                    entry = LexiconEntry(
                        alias=alias.lower(),
                        canonical=canonical.lower(),
                        drug_class=drug_class.lower(),
                        source_ref=source_ref,
                    )
                    
                    # Add to alias index
                    self._alias_to_entry[entry.alias] = entry
                    
                    # Add to class index
                    if entry.drug_class not in self._class_to_aliases:
                        self._class_to_aliases[entry.drug_class] = []
                    self._class_to_aliases[entry.drug_class].append(entry)
                    
                    total_entries += 1
            except Exception as e:
                # Log but don't fail - allow partial loads
                pass

        self._version = self._compute_version()
        self._last_loaded = time.time()

    def _compute_version(self) -> str:
        """Compute ontology version from source file modification times."""
        version_parts = []
        if self.sources_dir.exists():
            for f in sorted(self.sources_dir.glob("*.json")):
                try:
                    mtime = f.stat().st_mtime
                    version_parts.append(f"{f.name}:{int(mtime)}")
                except Exception:
                    version_parts.append(f"{f.name}:0")
        return "ontology-" + "-".join(version_parts) if version_parts else "ontology-base"

    def lookup(self, alias: str) -> Optional[LexiconEntry]:
        """Look up an alias and return the canonical form and drug class.

        Args:
            alias: The drug name, brand, or abbreviation to look up.

        Returns:
            LexiconEntry if found, None otherwise.
        """
        start = time.time()
        entry = self._alias_to_entry.get(alias.lower())
        elapsed_ms = (time.time() - start) * 1000
        
        # Performance monitoring (optional)
        if elapsed_ms > 10.0:
            # In production, this would be logged or monitored
            pass
        
        return entry

    def lookup_by_class(self, drug_class: str) -> List[LexiconEntry]:
        """Get all entries for a given drug class.

        Args:
            drug_class: The therapeutic class to query.

        Returns:
            List of LexiconEntry instances for the given class.
        """
        return self._class_to_aliases.get(drug_class.lower(), [])

    def get_statistics(self) -> Dict[str, Any]:
        """Get ontology statistics."""
        total_aliases = len(self._alias_to_entry)
        total_classes = len(self._class_to_aliases)
        total_entries = sum(len(v) for v in self._class_to_aliases.values())
        
        return {
            "ontology_version": self._version,
            "total_alias_entries": total_aliases,
            "total_drug_classes": total_classes,
            "total_source_entries": total_entries,
            "classes": list(self._class_to_aliases.keys()),
            "last_loaded_ms": int((time.time() - self._last_loaded) * 1000),
        }

    def get_aliases_for_class(self, drug_class: str) -> List[str]:
        """Get all aliases for a given drug class.

        Args:
            drug_class: The therapeutic class.

        Returns:
            List of alias strings.
        """
        entries = self.lookup_by_class(drug_class)
        return [e.alias for e in entries]


# Create a singleton instance for convenience
_ontology_instance: Optional[Ontology] = None


def get_ontology() -> Ontology:
    """Get the global ontology singleton instance."""
    global _ontology_instance
    if _ontology_instance is None:
        _ontology_instance = Ontology()
    return _ontology_instance


def reset_ontology():
    """Reset the ontology singleton (for testing)."""
    global _ontology_instance
    _ontology_instance = None


# Provide the v1 lexicon provider interface
class LexiconProviderV1:
    """v1 of the Lexicon Provider interface.

    Complies with the contract expected by GUARD and other consumers.
    """

    def __init__(self):
        self.ontology = get_ontology()
        self.version = "v1.0.0"

    def resolve_alias(self, alias: str) -> Optional[Dict[str, Any]]:
        """Resolve a drug alias to its canonical form and class.

        Args:
            alias: The drug name, brand, or abbreviation to resolve.

        Returns:
            Dict with keys: alias, canonical, drug_class, source_ref,
            or None if not found.
        """
        entry = self.ontology.lookup(alias)
        if entry is None:
            return None
        return {
            "alias": entry.alias,
            "canonical": entry.canonical,
            "drug_class": entry.drug_class,
            "source_ref": entry.source_ref,
        }

    def get_class_aliases(self, drug_class: str) -> List[Dict[str, str]]:
        """Get all aliases for a given drug class.

        Args:
            drug_class: The therapeutic class to query.

        Returns:
            List of dicts with alias and canonical keys.
        """
        entries = self.ontology.lookup_by_class(drug_class)
        return [
            {"alias": e.alias, "canonical": e.canonical}
            for e in entries
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get ontology statistics."""
        return self.ontology.get_statistics()

    def get_version(self) -> str:
        """Get the ontology version."""
        return self.ontology._version


# Convenience functions
def resolve(drug_name: str) -> Optional[Dict[str, Any]]:
    """Quick resolve function."""
    return get_ontology().lookup(drug_name)


def get_aliases(drug_class: str) -> List[str]:
    """Quick alias retrieval function."""
    return get_ontology().get_aliases_for_class(drug_class)


# Initialize the ontology on module import
_ontology_instance = Ontology()