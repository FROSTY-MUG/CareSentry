"""Unit tests for F-01 Drug Ontology and Normalizer."""

import time
import pytest
from caresentry_plus.ontology.normalizer import DrugNormalizer, NormalizedDrugEntity
from caresentry_plus.ontology.table import ONTOLOGY_VERSION, DRUG_ONTOLOGY_REGISTRY


@pytest.fixture
def normalizer():
    return DrugNormalizer()


def test_ontology_alias_count_threshold(normalizer):
    """F-01 Requirement: Total aliases indexed >= 150 entries."""
    assert normalizer.total_alias_count >= 150, f"Expected >= 150 aliases, got {normalizer.total_alias_count}"


def test_ontology_versioned(normalizer):
    """F-01 Requirement: Versioned ontology."""
    assert normalizer.ontology_version == ONTOLOGY_VERSION
    assert ONTOLOGY_VERSION == "1.0.0"


def test_penicillin_family_normalization(normalizer):
    """F-01 Requirement: Penicillin family resolution."""
    cases = [
        ("Augmentin", "amoxicillin/clavulanate", "penicillin"),
        ("PCN", "penicillin", "penicillin"),
        ("Amoxil", "amoxicillin", "penicillin"),
        ("Zosyn", "piperacillin/tazobactam", "penicillin"),
        ("Unasyn", "ampicillin", "penicillin"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_sulfa_family_normalization(normalizer):
    """F-01 Requirement: Sulfa family resolution."""
    cases = [
        ("Bactrim", "sulfamethoxazole/trimethoprim", "sulfonamide"),
        ("Septra DS", "sulfamethoxazole/trimethoprim", "sulfonamide"),
        ("TMP-SMX", "sulfamethoxazole/trimethoprim", "sulfonamide"),
        ("Sulfadiazine", "sulfadiazine", "sulfonamide"),
        ("Azulfidine", "sulfasalazine", "sulfonamide"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_nsaid_family_normalization(normalizer):
    """F-01 Requirement: NSAID family resolution."""
    cases = [
        ("Advil", "ibuprofen", "nsaid"),
        ("Motrin", "ibuprofen", "nsaid"),
        ("Aleve", "naproxen", "nsaid"),
        ("Toradol", "ketorolac", "nsaid"),
        ("Mobic", "meloxicam", "nsaid"),
        ("Celebrex", "celecoxib", "nsaid"),
        ("Aspirin", "aspirin", "nsaid"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_metformin_family_normalization(normalizer):
    """F-01 Requirement: Metformin family resolution."""
    cases = [
        ("Glucophage", "metformin", "biguanide"),
        ("Fortamet", "metformin", "biguanide"),
        ("Glumetza", "metformin", "biguanide"),
        ("Janumet", "metformin/sitagliptin", "biguanide"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_spironolactone_family_normalization(normalizer):
    """F-01 Requirement: Spironolactone family resolution."""
    cases = [
        ("Aldactone", "spironolactone", "aldosterone_antagonist"),
        ("CaroSpir", "spironolactone", "aldosterone_antagonist"),
        ("Inspra", "eplerenone", "aldosterone_antagonist"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_anticoagulant_family_normalization(normalizer):
    """F-01 Requirement: Anticoagulant family resolution."""
    cases = [
        ("Coumadin", "warfarin", "anticoagulant"),
        ("Eliquis", "apixaban", "anticoagulant"),
        ("Xarelto", "rivaroxaban", "anticoagulant"),
        ("Pradaxa", "dabigatran", "anticoagulant"),
        ("Lovenox", "enoxaparin", "anticoagulant"),
    ]
    for term, exp_canon, exp_class in cases:
        ent = normalizer.normalize(term)
        assert ent is not None, f"Failed to normalize {term}"
        assert ent.canonical_name == exp_canon
        assert ent.drug_class == exp_class


def test_lookup_latency_under_10ms(normalizer):
    """F-01 Requirement: Lookup latency strictly under 10 ms."""
    avg_latency_ms = normalizer.benchmark_latency(iterations=1000)
    assert avg_latency_ms < 10.0, f"Average lookup took {avg_latency_ms} ms, expected < 10ms"
    assert avg_latency_ms < 0.5  # In practice, hash lookup is < 0.05 ms


def test_extract_and_normalize_in_text(normalizer):
    """Test multi-entity extraction from narrative sentence."""
    text = "Patient was on Coumadin and Advil, with historical Augmentin reaction."
    entities = normalizer.extract_and_normalize(text)
    canonicals = {e.canonical_name for e in entities}
    assert "warfarin" in canonicals
    assert "ibuprofen" in canonicals
    assert "amoxicillin/clavulanate" in canonicals
