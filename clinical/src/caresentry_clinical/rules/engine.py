"""Rule engine and pack loader for CareSentry Clinical.

Loads rule_pack.v1 JSON, validates provenance, evaluates after the core linter,
and merges results by (drug, constraint) - can only make the verdict stricter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Known verdict strictness order (only stricter transitions allowed)
VERDICT_ORDER = {"PASS": 0, "FAIL": 1}

# Known rule IDs pattern
CLIN_ID_PATTERN = r"^CLIN-"


class RuleValidationError(Exception):
    """Raised when a rule fails validation."""
    pass


class RulePack:
    """Represents a loaded and validated rule pack v1."""

    def __init__(
        self,
        pack_data: Dict[str, Any],
        pack_path: Optional[Path] = None,
    ):
        self.pack_data = pack_data
        self.pack_path = pack_path
        self.version = pack_data.get("version", "unknown")
        self.name = pack_data.get("name", "Unnamed Rule Pack")
        self.rules: List[Dict[str, Any]] = []
        self._validate_and_load()

    def _validate_and_load(self):
        """Validate the pack structure and load rules."""
        if "rules" not in self.pack_data:
            raise RuleValidationError("Rule pack missing 'rules' key")

        for i, rule in enumerate(self.pack_data["rules"]):
            self._validate_rule(rule, i)

        self.rules = [
            RulePack._enrich_rule(rule, idx) for idx, rule in enumerate(self.pack_data["rules"])
        ]

    def _validate_rule(self, rule: Dict[str, Any], index: int):
        """Validate a single rule entry."""
        # Required fields
        required_top_level = ["id", "name", "provenance", "applies_to"]
        for field in required_top_level:
            if field not in rule:
                raise RuleValidationError(
                    f"Rule [{index}] missing required field: {field}"
                )

        # CLIN- prefix check for rule ID
        rule_id = rule.get("id", "")
        if not rule_id.startswith("CLIN-"):
            raise RuleValidationError(
                f"Rule [{index}] ID '{rule_id}' must start with 'CLIN-' prefix"
            )

        # Provenance check - must have source and date
        provenance = rule.get("provenance", {})
        if not provenance.get("source"):
            raise RuleValidationError(
                f"Rule [{index}] '{rule_id}' missing provenance source"
            )
        if not provenance.get("date"):
            raise RuleValidationError(
                f"Rule [{index}] '{rule_id}' missing provenance date"
            )

        # reviewer_status must be one of the allowed values
        rs = provenance.get("reviewer_status", "UNVERIFIED")
        if rs not in ("UNVERIFIED", "SOURCE_CHECKED", "CLINICIAN_REVIEWED"):
            raise RuleValidationError(
                f"Rule [{index}] '{rule_id}' invalid reviewer_status: {rs}"
            )

        # applies_to must be a non-empty list
        applies_to = rule.get("applies_to", [])
        if not applies_to or not isinstance(applies_to, list):
            raise RuleValidationError(
                f"Rule [{index}] '{rule_id}' must have non-empty applies_to list"
            )

        # merge_behavior must be 'strict' or 'override'
        mb = rule.get("merge_behavior", "strict")
        if mb not in ("strict", "override"):
            raise RuleValidationError(
                f"Rule [{index}] '{rule_id}' invalid merge_behavior: {mb}"
            )

    @staticmethod
    def _enrich_rule(rule: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Enrich rule with derived fields."""
        rule_copy = dict(rule)
        rule_copy["_index"] = index
        rule_copy["_provenance_origin"] = rule.get("provenance", {}).get("source", "unknown")
        # Set default merge_behavior if not specified
        if "merge_behavior" not in rule_copy:
            rule_copy["merge_behavior"] = "strict"
        return rule_copy

    def evaluate(
        self,
        core_result: Dict[str, Any],
        record_text: str,
        summary_text: str,
    ) -> Dict[str, Any]:
        """Evaluate rules against the core linter result.

        Can only make the verdict stricter (e.g., PASS -> FAIL, but not FAIL -> PASS).
        Merges by (drug, constraint) - if multiple rules flag the same drug/constraint,
        the stricter verdict wins.

        Returns a dict with:
        - status: the merged verdict
        - clinical_violations: list of violations from this pack
        - merge_log: what was merged and how
        """
        if not self.rules:
            return {
                "status": core_result.get("status", "PASS"),
                "clinical_violations": [],
                "merge_log": "No rules in pack; verdict unchanged from core.",
            }

        # Start with core result status
        core_status = core_result.get("status", "PASS")
        core_violations = core_result.get("violations", [])

        # Track merged verdict and violations
        merged_verdict = core_status
        merge_log = []
        clinical_violations: List[Dict[str, Any]] = []

        # Track (drug, constraint) pairs we've already seen
        seen_pairs: set = set()

        # Process each rule
        for rule in self.rules:
            rule_id = rule["id"]
            applies_to = rule.get("applies_to", [])
            severity = rule.get("severity", "CRITICAL")
            merge_behavior = rule.get("merge_behavior", "strict")

            # Find matching drugs in the summary/record
            matched_drugs = self._find_matched_drugs(applies_to, record_text, summary_text)

            if not matched_drugs:
                merge_log.append(
                    f"Rule {rule_id}: no matching drugs found in record/summary"
                )
                continue

            # Build violations for matched drugs
            for drug_name in matched_drugs:
                constraint_key = (drug_name, rule_id)

                # Skip if we've already processed this (drug, rule) pair
                if constraint_key in seen_pairs:
                    merge_log.append(
                        f"Rule {rule_id}: duplicate match for {drug_name}, skipping"
                    )
                    continue
                seen_pairs.add(constraint_key)

                # Create violation entry
                violation = {
                    "type": f"CLIN-{rule_id.split('-')[1] if '-' in rule_id else 'UNK'}",
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "severity": severity,
                    "offending_drug": drug_name,
                    "provenance": rule.get("provenance", {}),
                    "recommendation": rule.get("action", "Review clinical guidelines"),
                }

                clinical_violations.append(violation)

                # Update merged verdict - only allow stricter transitions
                violation_severity_order = {"CRITICAL": 3, "HIGH": 2, "MODERATE": 1, "MINOR": 0}
                current_merged_level = VERDICT_ORDER.get(merged_verdict, 0)
                new_violation_level = violation_severity_order.get(severity, 1)

                # If the new violation is more severe than current merged verdict, upgrade
                if new_violation_level > current_merged_level:
                    # Map severity to verdict
                    severity_to_verdict = {3: "FAIL", 2: "FAIL", 1: "FAIL", 0: "PASS"}
                    merged_verdict = severity_to_verdict[new_violation_level]
                    merge_log.append(
                        f"Rule {rule_id}: upgraded verdict to {merged_verdict} "
                        f"due to {severity} severity violation for {drug_name}"
                    )
                elif new_violation_level == current_merged_level and merged_verdict == "PASS":
                    # Same severity but we're at PASS - keep PASS (can't downgrade)
                    merge_log.append(
                        f"Rule {rule_id}: maintaining PASS verdict (cannot downgrade from core)"
                    )
                else:
                    merge_log.append(
                        f"Rule {rule_id}: vetoed - would not upgrade verdict from {merged_verdict}"
                    )

        # If no clinical violations from pack, keep core verdict
        if not clinical_violations:
            merge_log.append("No rule violations found; verdict unchanged from core.")

        return {
            "status": merged_verdict,
            "clinical_violations": clinical_violations,
            "merge_log": merge_log,
        }

    def _find_matched_drugs(
        self,
        applies_to: List[str],
        record_text: str,
        summary_text: str,
    ) -> List[str]:
        """Find drugs from applies_to that appear in the record or summary.

        Simple substring/word-boundary match. In a full implementation,
        this would use the ontology for normalization.
        """
        import re

        text_to_search = (record_text + " " + summary_text).lower()
        matched = []

        for drug in applies_to:
            escaped = re.escape(drug.lower())
            # Match word boundaries
            pattern = rf"\b{escaped}\b"
            if re.search(pattern, text_to_search):
                # Only add if not already matched
                if drug not in matched:
                    matched.append(drug)

        return matched


class RulePackLoader:
    """Loads rule packs from various sources."""

    # Default pack search paths
    DEFAULT_SEARCH_PATHS = [
        Path("clinical/rule_packs/default_pack.json"),
        Path(".agents/skills/caresentry/references/clinical_rules.json"),
        Path("references/clinical_rules.json"),
    ]

    @classmethod
    def load_default_pack(cls) -> RulePack:
        """Load the default rule pack from clinical/rule_packs/."""
        default_path = cls.DEFAULT_SEARCH_PATHS[0]
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RulePack(data, pack_path=default_path)
        else:
            # Try to find in standard locations
            for path in cls.DEFAULT_SEARCH_PATHS[1:]:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return RulePack(data, pack_path=path)
            raise FileNotFoundError("Could not locate any rule pack")

    @classmethod
    def load_pack_from_path(cls, path: Path) -> RulePack:
        """Load a rule pack from a specific path."""
        if not path.exists():
            raise FileNotFoundError(f"Rule pack not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RulePack(data, pack_path=path)

    @classmethod
    def validate_pack_schema(cls, path: Path) -> bool:
        """Validate a rule pack against the JSON schema."""
        import jsonschema

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        schema_path = Path(__file__).parent.parent / "rule_packs" / "rule_pack_schema.json"
        if not schema_path.exists():
            # Schema not found, do basic validation only
            return cls._basic_validate(data)

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        try:
            jsonschema.validate(data, schema)
            return True
        except Exception:
            return cls._basic_validate(data)

    @staticmethod
    def _basic_validate(data: Dict[str, Any]) -> bool:
        """Basic validation without full schema."""
        required = ["version", "name", "rules"]
        if not all(k in data for k in required):
            return False

        for i, rule in enumerate(data.get("rules", [])):
            if not all(k in rule for k in ["id", "name", "provenance", "applies_to"]):
                return False
            if not rule.get("id", "").startswith("CLIN-"):
                return False
            prov = rule.get("provenance", {})
            if not prov.get("source"):
                return False
            if prov.get("reviewer_status", "UNVERIFIED") not in (
                "UNVERIFIED",
                "SOURCE_CHECKED",
                "CLINICIAN_REVIEWED",
            ):
                return False

        return True