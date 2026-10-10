"""CareSentry Guard Built-in Offline Clinical Drug Lexicon (RxNorm & ATC Lite).

Citations & Provenance:
- NLM RxNorm Standard Drug Nomenclature (2024-05 Release)
- WHO Collaborating Centre for Drug Statistics Methodology: ATC/DDD Index 2024
- American Geriatrics Society (AGS) 2023 Updated Beers Criteria
- Clinical Pharmacogenetics Implementation Consortium (CPIC) Guidelines
"""

from __future__ import annotations

import difflib
import re
from typing import Dict, List, Optional, Set, Tuple

from caresentry_guard.lexicon.provider import BaseLexiconProvider

# Clinically audited drug ontology with codes and trade names
DRUG_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    # --- PENICILLINS (ATC: J01C) ---
    "amoxicillin": {
        "generic": "amoxicillin",
        "allergy_classes": ["penicillin", "beta_lactam"],
        "brands": ["amoxil", "moxatag", "trimox", "wymox"],
        "misspellings": ["amoxacillin", "amoxilillin", "amoxcillin"],
        "atc": "J01CA04",
        "rxcui": "723",
        "cross_reactivity": {"cephalosporin_1st_gen": "HIGH", "cephalosporin_3rd_gen": "LOW"},
    },
    "amoxicillin-clavulanate": {
        "generic": "amoxicillin-clavulanate",
        "allergy_classes": ["penicillin", "beta_lactam"],
        "brands": ["augmentin", "augmentin xr", "clavulin"],
        "misspellings": ["augmetin", "augmentan", "amox-clav"],
        "atc": "J01CR02",
        "rxcui": "617314",
    },
    "ampicillin": {
        "generic": "ampicillin",
        "allergy_classes": ["penicillin", "beta_lactam"],
        "brands": ["principen", "omnipen"],
        "atc": "J01CA01",
        "rxcui": "733",
    },
    "piperacillin-tazobactam": {
        "generic": "piperacillin-tazobactam",
        "allergy_classes": ["penicillin", "beta_lactam"],
        "brands": ["zosyn", "tazocin"],
        "atc": "J01CR05",
        "rxcui": "211516",
    },
    "penicillin": {
        "generic": "penicillin",
        "allergy_classes": ["penicillin", "beta_lactam"],
        "brands": ["penicillin vk", "veetids", "bicillin", "penicillin g"],
        "misspellings": ["penicilin", "pcn", "penecillin"],
        "atc": "J01CE01",
        "rxcui": "7980",
    },
    # --- CEPHALOSPORINS (ATC: J01D) ---
    "cephalexin": {
        "generic": "cephalexin",
        "allergy_classes": ["cephalosporin", "beta_lactam"],
        "brands": ["keflex", "keftab"],
        "atc": "J01DB01",
        "rxcui": "2231",
        "cross_reacts_with": ["penicillin"],
    },
    "cefazolin": {
        "generic": "cefazolin",
        "allergy_classes": ["cephalosporin", "beta_lactam"],
        "brands": ["ancef", "kefzol"],
        "atc": "J01DB04",
        "rxcui": "2180",
        "cross_reacts_with": ["penicillin"],
    },
    "ceftriaxone": {
        "generic": "ceftriaxone",
        "allergy_classes": ["cephalosporin", "beta_lactam"],
        "brands": ["rocephin"],
        "atc": "J01DD04",
        "rxcui": "2193",
    },
    # --- SULFONAMIDES (ATC: J01E) ---
    "trimethoprim-sulfamethoxazole": {
        "generic": "trimethoprim-sulfamethoxazole",
        "allergy_classes": ["sulfa", "sulfonamide"],
        "brands": ["bactrim", "bactrim ds", "septra", "septra ds", "cotrimoxazole", "tmp-smx"],
        "misspellings": ["backtrim", "bactram", "septrin"],
        "atc": "J01EE01",
        "rxcui": "10831",
    },
    "sulfasalazine": {
        "generic": "sulfasalazine",
        "allergy_classes": ["sulfa", "sulfonamide"],
        "brands": ["azulfidine"],
        "atc": "A07EC01",
        "rxcui": "10168",
    },
    # --- NSAIDS (ATC: M01A) ---
    "ibuprofen": {
        "generic": "ibuprofen",
        "allergy_classes": ["nsaid", "nsaids", "aspirin"],
        "brands": ["advil", "motrin", "nuprin", "caldolor"],
        "misspellings": ["ibuprophen", "ibruprofen", "ibuprofin"],
        "atc": "M01AE01",
        "rxcui": "5640",
    },
    "naproxen": {
        "generic": "naproxen",
        "allergy_classes": ["nsaid", "nsaids", "aspirin"],
        "brands": ["aleve", "naprosyn", "anaprox"],
        "atc": "M01AE02",
        "rxcui": "7258",
    },
    "meloxicam": {
        "generic": "meloxicam",
        "allergy_classes": ["nsaid", "nsaids"],
        "brands": ["mobic", "vivlodex"],
        "atc": "M01AC06",
        "rxcui": "31407",
    },
    "ketorolac": {
        "generic": "ketorolac",
        "allergy_classes": ["nsaid", "nsaids"],
        "brands": ["toradol", "sprix"],
        "atc": "M01AB15",
        "rxcui": "6142",
    },
    "aspirin": {
        "generic": "aspirin",
        "allergy_classes": ["nsaid", "nsaids", "salicylate", "aspirin"],
        "brands": ["bayer", "ecotrin", "bufferin"],
        "atc": "B01AC06",
        "rxcui": "1191",
    },
    # --- FLUOROQUINOLONES (ATC: J01M) ---
    "ciprofloxacin": {
        "generic": "ciprofloxacin",
        "allergy_classes": ["fluoroquinolone", "fluoroquinolones", "quinolone"],
        "brands": ["cipro", "cipro xr"],
        "misspellings": ["ciprofloxicin", "ciproflox"],
        "atc": "J01MA02",
        "rxcui": "2551",
    },
    "levofloxacin": {
        "generic": "levofloxacin",
        "allergy_classes": ["fluoroquinolone", "fluoroquinolones", "quinolone"],
        "brands": ["levaquin"],
        "atc": "J01MA12",
        "rxcui": "82122",
    },
    # --- RENAL / METABOLIC ---
    "metformin": {
        "generic": "metformin",
        "allergy_classes": ["biguanide"],
        "brands": ["glucophage", "glucophage xr", "fortamet", "glumetza", "riomet"],
        "atc": "A10BA02",
        "rxcui": "6809",
        "renal_egfr_cutoff": 30.0,
    },
    "spironolactone": {
        "generic": "spironolactone",
        "allergy_classes": ["aldosterone_antagonist"],
        "brands": ["aldactone", "carospir"],
        "atc": "C03DA01",
        "rxcui": "9997",
        "renal_egfr_cutoff": 30.0,
    },
    # --- HIGH RISK INTERACTIONS & BEERS CRITERIA ---
    "warfarin": {
        "generic": "warfarin",
        "allergy_classes": ["anticoagulant"],
        "brands": ["coumadin", "jantoven"],
        "atc": "B01AA03",
        "rxcui": "11289",
        "interacts_with": ["ibuprofen", "naproxen", "meloxicam", "ketorolac", "aspirin", "celecoxib", "diclofenac"],
    },
    "diphenhydramine": {
        "generic": "diphenhydramine",
        "allergy_classes": ["antihistamine"],
        "brands": ["benadryl", "sominex", "unisom"],
        "atc": "R06AA02",
        "rxcui": "3498",
        "beers_criteria": "Strongly anticholinergic, high risk of delirium, sedation, falls and cognitive impairment in elderly",
    },
}


class RxNormLiteProvider(BaseLexiconProvider):
    """Production offline clinical drug ontology provider."""

    def __init__(self):
        # Build inverted lookup term -> generic entry
        self._term_to_entry: Dict[str, Dict[str, Any]] = {}
        for generic, data in DRUG_ONTOLOGY.items():
            all_terms = {generic}
            all_terms.update(data.get("brands", []))
            all_terms.update(data.get("misspellings", []))
            for t in all_terms:
                self._term_to_entry[t.lower().strip()] = data

    def get_terms_for_allergy(self, allergy_class: str) -> Set[str]:
        """Return all matching generic, brand and misspelling terms for an allergy class."""
        norm_class = allergy_class.lower().replace("-", "_").replace(" ", "_").strip()
        matched: Set[str] = set()

        for generic, data in DRUG_ONTOLOGY.items():
            classes = [c.lower() for c in data.get("allergy_classes", [])]
            # Match directly or check cross-reactivity
            is_match = any(norm_class in c or c in norm_class for c in classes)
            if "penicillin" in norm_class and data.get("cross_reacts_with"):
                if "penicillin" in data.get("cross_reacts_with", []):
                    is_match = True

            if is_match:
                matched.add(generic)
                matched.update(data.get("brands", []))
                matched.update(data.get("misspellings", []))

        return matched

    def map_to_generic(self, term: str) -> Optional[str]:
        term_clean = term.lower().strip()
        if term_clean in self._term_to_entry:
            return self._term_to_entry[term_clean]["generic"]
        
        # Fuzzy match for minor typos (>= 85% similarity)
        candidates = difflib.get_close_matches(term_clean, self._term_to_entry.keys(), n=1, cutoff=0.85)
        if candidates:
            return self._term_to_entry[candidates[0]]["generic"]
        return None

    def get_atc_code(self, term: str) -> Optional[str]:
        generic = self.map_to_generic(term)
        if generic and generic in DRUG_ONTOLOGY:
            return DRUG_ONTOLOGY[generic].get("atc")
        return None

    def get_rxnorm_cui(self, term: str) -> Optional[str]:
        generic = self.map_to_generic(term)
        if generic and generic in DRUG_ONTOLOGY:
            return DRUG_ONTOLOGY[generic].get("rxcui")
        return None

    def check_allergy_clash(
        self, candidate_drug: str, documented_allergies: List[str]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        candidate_clean = candidate_drug.lower().strip()
        generic = self.map_to_generic(candidate_clean)
        if not generic:
            return False, None, None

        entry = DRUG_ONTOLOGY.get(generic, {})
        entry_classes = [c.lower() for c in entry.get("allergy_classes", [])]

        for allergy in documented_allergies:
            norm_a = allergy.lower().replace("-", "_").strip()
            # Direct class clash
            if any(norm_a in c or c in norm_a for c in entry_classes):
                return True, allergy, f"Direct allergy contraindication ({entry.get('atc', 'ATC-Unspecified')})"
            
            # Cross reactivity check (e.g. penicillin -> cephalosporins)
            if "penicillin" in norm_a and "cephalosporin" in entry_classes:
                return True, allergy, "Cephalosporin cross-reactivity with documented penicillin allergy (beta-lactam ring similarity)"

        return False, None, None

    def get_all_known_drugs(self) -> Set[str]:
        """Return full vocabulary of known drug tokens."""
        return set(self._term_to_entry.keys())
