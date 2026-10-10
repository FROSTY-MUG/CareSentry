"""CareSentry-AI Plus Invariant Rule Pack Engine.

Executes extended clinical invariant checks:
- Cross-reactivity (epitope & side-chain homology)
- Dose-aware renal clearance thresholds (Cockcroft-Gault & CKD-EPI)
- AGS Beers Criteria geriatric appropriateness (age >= 65)
- High-risk drug-drug interactions
- Duplicate therapeutic class duplication
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema

from caresentry_plus.ontology.normalizer import DrugNormalizer, NormalizedDrugEntity
from caresentry_plus.rules.context_filter import AssertionStatus, ContextFilter
from caresentry_plus.rules.renal import resolve_effective_renal_clearance

logger = logging.getLogger("caresentry_plus.rules.engine")

DEFAULT_RULE_PACKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "rule_packs"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "contracts" / "rule_pack.v1.schema.json"


class RulePackEngine:
    """Loads, validates, and evaluates versioned invariant rule packs."""

    def __init__(
        self,
        rule_packs_dir: Optional[Path] = None,
        normalizer: Optional[DrugNormalizer] = None,
        context_filter: Optional[ContextFilter] = None,
        validate_schema: bool = True,
    ):
        self.rule_packs_dir = rule_packs_dir or DEFAULT_RULE_PACKS_DIR
        self.normalizer = normalizer or DrugNormalizer()
        self.context_filter = context_filter or ContextFilter()
        self.validate_schema = validate_schema
        self.schema = self._load_schema()
        self.rule_packs: Dict[str, Dict[str, Any]] = {}
        self.loaded_pack_ids: List[str] = []
        self._load_all_packs()

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        """Load contract schema for rule pack validation."""
        if SCHEMA_PATH.exists():
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _load_all_packs(self) -> None:
        """Scan directory and load all JSON rule packs."""
        if not self.rule_packs_dir.exists():
            logger.warning(f"Rule packs directory not found: {self.rule_packs_dir}")
            return

        for p in self.rule_packs_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    pack_data = json.load(f)

                if self.validate_schema and self.schema:
                    jsonschema.validate(instance=pack_data, schema=self.schema)

                pack_id = pack_data.get("pack_id", p.stem)
                self.rule_packs[pack_id] = pack_data
                self.loaded_pack_ids.append(pack_id)
            except Exception as e:
                logger.error(f"Failed to load/validate rule pack {p.name}: {e}")
                raise

    def evaluate_invariants(
        self,
        patient_record: str,
        summary_content: str,
        patient_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate all loaded rule packs against patient record and generated summary."""
        patient_metadata = patient_metadata or {}
        violations: List[Dict[str, Any]] = []

        # 1. Normalize summary orders
        summary_entities = self.normalizer.extract_and_normalize(summary_content)
        summary_canonicals = {e.canonical_name: e for e in summary_entities}
        summary_classes = {e.drug_class: e for e in summary_entities}

        # 2. Extract demographics and labs from metadata or record
        age = patient_metadata.get("age")
        weight_kg = patient_metadata.get("weight_kg")
        is_female = patient_metadata.get("is_female")
        stated_egfr = patient_metadata.get("egfr")
        serum_creatinine = patient_metadata.get("creatinine")

        # Auto-extract if missing
        if age is None:
            import re
            age_m = re.search(r"\b(\d{1,3})\s*[- ]?\s*(?:year[s]?[- ]?old|yo|y\.o\.)\b", patient_record, re.IGNORECASE)
            if age_m:
                age = int(age_m.group(1))

        if is_female is None:
            import re
            if re.search(r"\b(?:female|woman|lady|she|her)\b", patient_record, re.IGNORECASE):
                is_female = True
            elif re.search(r"\b(?:male|man|gentleman|he|his)\b", patient_record, re.IGNORECASE):
                is_female = False

        if weight_kg is None:
            import re
            wt_m = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*(?:kg|kilos)\b", patient_record, re.IGNORECASE)
            if wt_m:
                weight_kg = float(wt_m.group(1))

        if stated_egfr is None:
            import re
            egfr_m = re.search(r"(?:\(?egfr\)?|gfr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,3}(?:\.[0-9]+)?)", patient_record, re.IGNORECASE)
            if egfr_m:
                stated_egfr = float(egfr_m.group(1))

        if serum_creatinine is None:
            import re
            creat_m = re.search(r"(?:creatinine|creat|scr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,2}(?:\.[0-9]+)?)", patient_record, re.IGNORECASE)
            if creat_m:
                serum_creatinine = float(creat_m.group(1))

        eff_egfr, eff_crcl, calc_method = resolve_effective_renal_clearance(
            stated_egfr=stated_egfr,
            serum_creatinine=serum_creatinine,
            age=age,
            weight_kg=weight_kg,
            is_female=is_female,
        )

        # 3. Context analysis for allergies and active meds in EHR
        record_entities = self.normalizer.extract_and_normalize(patient_record)

        # Check all rules in packs
        for pack_id, pack in self.rule_packs.items():
            for rule in pack.get("rules", []):
                r_type = rule.get("type")
                r_id = rule.get("id")
                trigger = rule.get("trigger", {})
                condition = rule.get("condition", {})
                severity = rule.get("severity", "HIGH")
                msg = rule.get("message", "")
                provenance = rule.get("provenance", {})

                # --- A. Cross-Reactivity Rules ---
                if r_type == "cross_reactivity":
                    trig_class = trigger.get("drug_class")
                    # Check if patient record has affirmed allergy to this drug class
                    for r_ent in record_entities:
                        if r_ent.drug_class == trig_class or r_ent.canonical_name in trigger.get("target_drugs", []):
                            # Analyze context assertion
                            assertion = self.context_filter.analyze_assertion(patient_record, r_ent.raw_term)
                            if assertion.is_active_risk:
                                # Check if summary orders any caution / contraindicated drugs
                                caution_drugs = [d.lower() for d in condition.get("caution_drugs", [])]
                                contra_drugs = [d.lower() for d in condition.get("contraindicated_drugs", [])]
                                all_targets = caution_drugs + contra_drugs

                                for target_name in all_targets:
                                    norm_target = self.normalizer.normalize(target_name)
                                    target_canonical = norm_target.canonical_name if norm_target else target_name

                                    if target_canonical in summary_canonicals:
                                        matched_summary_ent = summary_canonicals[target_canonical]
                                        violations.append({
                                            "rule_id": r_id,
                                            "type": r_type,
                                            "severity": severity,
                                            "message": msg,
                                            "offending_drug": matched_summary_ent.raw_term,
                                            "evidence": f"Patient has documented {r_ent.raw_term} ({assertion.status.value}) allergy; summary prescribes cross-reactive {matched_summary_ent.raw_term}.",
                                            "provenance": provenance,
                                        })
                                        break

                # --- B. Dose-Aware Renal Rules ---
                elif r_type == "dose_aware_renal":
                    target_drugs = [d.lower() for d in trigger.get("target_drugs", [])]
                    egfr_cutoff = condition.get("egfr_cutoff_ml_min", 30.0)
                    crcl_cutoff = condition.get("crcl_cutoff_ml_min", 30.0)

                    # Check if patient renal clearance is below threshold
                    renal_impaired = False
                    observed_val = None
                    cutoff_val = None

                    if eff_egfr is not None and eff_egfr < egfr_cutoff:
                        renal_impaired = True
                        observed_val = eff_egfr
                        cutoff_val = egfr_cutoff
                    elif eff_crcl is not None and eff_crcl < crcl_cutoff:
                        renal_impaired = True
                        observed_val = eff_crcl
                        cutoff_val = crcl_cutoff

                    if renal_impaired:
                        for td in target_drugs:
                            norm_td = self.normalizer.normalize(td)
                            td_canonical = norm_td.canonical_name if norm_td else td

                            if td_canonical in summary_canonicals:
                                offending = summary_canonicals[td_canonical]
                                violations.append({
                                    "rule_id": r_id,
                                    "type": r_type,
                                    "severity": severity,
                                    "message": msg,
                                    "offending_drug": offending.raw_term,
                                    "calculated_metric": observed_val,
                                    "threshold": cutoff_val,
                                    "evidence": f"Patient renal clearance ({calc_method}: {observed_val} mL/min) is below safe cutoff ({cutoff_val} mL/min) for {offending.raw_term}.",
                                    "provenance": provenance,
                                })
                                break

                # --- C. Geriatric Beers Criteria Rules ---
                elif r_type == "geriatric_beers":
                    age_min = trigger.get("age_min", 65)
                    if age is not None and age >= age_min:
                        contra_drugs = [d.lower() for d in condition.get("contraindicated_drugs", [])]
                        for cd in contra_drugs:
                            norm_cd = self.normalizer.normalize(cd)
                            cd_canonical = norm_cd.canonical_name if norm_cd else cd

                            if cd_canonical in summary_canonicals:
                                offending = summary_canonicals[cd_canonical]
                                violations.append({
                                    "rule_id": r_id,
                                    "type": r_type,
                                    "severity": severity,
                                    "message": msg,
                                    "offending_drug": offending.raw_term,
                                    "calculated_metric": age,
                                    "threshold": age_min,
                                    "evidence": f"Patient age {age} >= {age_min}. Inappropriate prescription of high-risk medication: {offending.raw_term}.",
                                    "provenance": provenance,
                                })
                                break

                # --- D. Drug-Drug Interaction Rules ---
                elif r_type == "drug_drug_interaction":
                    target_drugs = [d.lower() for d in trigger.get("target_drugs", [])]
                    contra_drugs = [d.lower() for d in condition.get("contraindicated_drugs", [])]

                    # Drug A can be either in active patient meds or in summary orders
                    drug_a_present = None
                    for td in target_drugs:
                        norm_td = self.normalizer.normalize(td)
                        td_canonical = norm_td.canonical_name if norm_td else td
                        if td_canonical in summary_canonicals:
                            drug_a_present = summary_canonicals[td_canonical]
                            break
                        for r_ent in record_entities:
                            if r_ent.canonical_name == td_canonical:
                                assertion = self.context_filter.analyze_assertion(patient_record, r_ent.raw_term)
                                if assertion.is_active_risk:
                                    drug_a_present = r_ent
                                    break

                    if drug_a_present:
                        for cd in contra_drugs:
                            norm_cd = self.normalizer.normalize(cd)
                            cd_canonical = norm_cd.canonical_name if norm_cd else cd
                            if cd_canonical in summary_canonicals:
                                offending_b = summary_canonicals[cd_canonical]
                                violations.append({
                                    "rule_id": r_id,
                                    "type": r_type,
                                    "severity": severity,
                                    "message": msg,
                                    "offending_drug": offending_b.raw_term,
                                    "interacting_drug": drug_a_present.raw_term,
                                    "evidence": f"Dangerous drug pair ordered: {drug_a_present.raw_term} interacts with {offending_b.raw_term}.",
                                    "provenance": provenance,
                                })
                                break

                # --- E. Duplicate Therapy Rules ---
                elif r_type == "duplicate_therapy":
                    dup_class = trigger.get("drug_class")
                    if dup_class:
                        matched_in_class = [e for e in summary_entities if e.drug_class == dup_class]
                        # Check distinct canonical drugs
                        unique_canonicals = {e.canonical_name: e for e in matched_in_class}
                        if len(unique_canonicals) >= 2:
                            drug_names = [e.raw_term for e in unique_canonicals.values()]
                            violations.append({
                                "rule_id": r_id,
                                "type": r_type,
                                "severity": severity,
                                "message": msg,
                                "offending_drug": ", ".join(drug_names),
                                "evidence": f"Multiple concurrent agents ({', '.join(drug_names)}) prescribed within same class '{dup_class}'.",
                                "provenance": provenance,
                            })

        return violations
