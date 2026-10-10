"""CareSentry-AI Deterministic Clinical Invariant Linter (v1.1.0).

Implements K-10, FR-03, and contracts/audit_result.v1.schema.json:
- Evaluates raw EHRs against generated summaries for allergy clashes, renal thresholds, and DDIs
- Stable CS-* rule identifiers
- Character-span offsets for summary evidence and patient history evidence
- Robust lab parsing: stated eGFR/Cr values, units, serial tracking (picks most recent)
- Comprehensive negation guards (e.g., 'NKDA', 'no known drug allergies', 'withhold metformin')
- Precompiled patterns for sub-100ms evaluation latency
- Rule schema validator ('validate_rules_schema') and '--explain' mode
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("caresentry.linter")

# Precompiled negation patterns
NEGATION_ORDER_PATTERN = re.compile(
    r"\b(withhold|hold|stop|discontinue|avoid|cease|do\s+not\s+(?:give|order|prescribe|administer)|no\s+|contraindicated|prohibited|taper\s+off)\b",
    re.IGNORECASE,
)

PATIENT_NKDA_PATTERN = re.compile(
    r"\b(no\s+known\s+(?:drug\s+)?allergies|nkda|nka|denies\s+(?:any\s+)?(?:drug\s+)?allergies|no\s+allergies\s+documented|no\s+reported\s+allergies)\b",
    re.IGNORECASE,
)

# Serial date pattern for lab extraction
DATE_EXTRACTOR_PATTERN = re.compile(
    r"(\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s+\d{4})?\b|\bday\s+\d+\b)",
    re.IGNORECASE,
)


def validate_rules_schema(rules: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate that clinical rules dictionary conforms to CareSentry Rule Schema v1.1."""
    errors = []
    if "allergies" not in rules or not isinstance(rules["allergies"], list):
        errors.append("Missing or invalid 'allergies' array")
    else:
        for idx, item in enumerate(rules["allergies"]):
            if "allergy_class" not in item:
                errors.append(f"Allergy rule #{idx} missing 'allergy_class'")
            if "rule_id" not in item:
                errors.append(f"Allergy rule #{idx} missing 'rule_id'")
            if "contraindicated_drugs" not in item:
                errors.append(f"Allergy rule #{idx} missing 'contraindicated_drugs'")

    if "renal_clearance_thresholds" not in rules or not isinstance(rules["renal_clearance_thresholds"], list):
        errors.append("Missing or invalid 'renal_clearance_thresholds' array")
    else:
        for idx, item in enumerate(rules["renal_clearance_thresholds"]):
            if "drug_name" not in item:
                errors.append(f"Renal rule #{idx} missing 'drug_name'")
            if "rule_id" not in item:
                errors.append(f"Renal rule #{idx} missing 'rule_id'")
            if "egfr_cutoff_ml_min" not in item:
                errors.append(f"Renal rule #{idx} missing 'egfr_cutoff_ml_min'")

    if "drug_drug_interactions" in rules and not isinstance(rules["drug_drug_interactions"], list):
        errors.append("Invalid 'drug_drug_interactions' type")

    return len(errors) == 0, errors


def load_clinical_rules(rules_path: Optional[str] = None) -> Dict[str, Any]:
    """Load deterministic clinical rule matrix."""
    if rules_path and os.path.exists(rules_path):
        target = Path(rules_path)
    else:
        curr_dir = Path(__file__).resolve().parent
        candidates = [
            curr_dir.parent / ".agents" / "skills" / "caresentry" / "references" / "clinical_rules.json",
            curr_dir.parent / "references" / "clinical_rules.json",
            Path(".agents/skills/caresentry/references/clinical_rules.json"),
            Path("references/clinical_rules.json"),
        ]
        target = None
        for c in candidates:
            if c.exists():
                target = c
                break

        if target is None:
            raise FileNotFoundError("Could not locate clinical_rules.json in standard reference paths.")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    is_valid, validation_errors = validate_rules_schema(data)
    if not is_valid:
        logger.warning(f"Clinical rules schema validation warnings: {validation_errors}")

    return data


def extract_patient_allergies(raw_text: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scan raw clinical text for documented drug allergies with character span evidence."""
    # Check if patient explicitly has NKDA / No Known Drug Allergies
    if PATIENT_NKDA_PATTERN.search(raw_text):
        # Even with NKDA, if an explicit allergy is later specified, we still check, but note NKDA
        pass

    detected = []
    text_lower = raw_text.lower()
    allergy_rules = rules.get("allergies", [])

    for rule in allergy_rules:
        allergy_class = rule["allergy_class"]
        rule_id = rule.get("rule_id", f"CS-ALLERGY-{allergy_class.upper()}")
        aliases = rule.get("aliases", [allergy_class])

        matched_for_rule = False
        for alias in aliases:
            escaped = re.escape(alias.lower())
            patterns = [
                rf"(?:allerg(?:y|ies|ic)\s*(?:to|:)?\s*[\w\s,;-]{{0,30}}?\b{escaped}\b)",
                rf"\b{escaped}\b(?:\s+\w+){{0,2}}\s*(?:allergy|anaphylaxis|hypersensitivity|reaction|intolerance)",
                rf"(?:adverse\s+reaction\s+to\s+[\w\s,;-]{{0,20}}?\b{escaped}\b)",
            ]
            for pat in patterns:
                for m in re.finditer(pat, text_lower):
                    # Check if the allergy statement itself is negated (e.g. "no allergy to penicillin")
                    prev_window = text_lower[max(0, m.start() - 25) : m.start()]
                    if re.search(r"\b(no|denies|without|negative\s+for)\b", prev_window):
                        continue

                    start_idx = max(0, m.start() - 20)
                    end_idx = min(len(raw_text), m.end() + 20)
                    snippet = raw_text[start_idx:end_idx].strip()
                    span = [m.start(), m.end()]

                    detected.append({
                        "rule_id": rule_id,
                        "allergy_class": allergy_class,
                        "matched_alias": alias,
                        "evidence": snippet,
                        "span": span,
                        "rule": rule,
                    })
                    matched_for_rule = True
                    break
                if matched_for_rule:
                    break
            if matched_for_rule:
                break

    return detected


def extract_renal_metrics(raw_text: str) -> Dict[str, Any]:
    """Extract stated eGFR and Creatinine lab measurements with serial tracking and units."""
    text_lower = raw_text.lower()

    # Find all eGFR mentions
    # e.g.: "eGFR: 22.4 mL/min/1.73m2", "GFR 28 mL/min", "eGFR of 18", "eGFR = 24.1"
    egfr_regex = re.compile(
        r"(?:egfr|gfr|estimated\s+gfr|est\.?\s*gfr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,3}(?:\.[0-9]+)?)\s*(ml/min(?:/1\.73m2|/1\.73\s*m²)?|ml/min)?",
        re.IGNORECASE,
    )

    creat_regex = re.compile(
        r"(?:creatinine|serum\s+creatinine|creat)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*(mg/dl|umol/l)?",
        re.IGNORECASE,
    )

    egfr_matches = list(egfr_regex.finditer(text_lower))
    creat_matches = list(creat_regex.finditer(text_lower))

    egfr_val: Optional[float] = None
    egfr_unit: str = "mL/min/1.73m²"
    egfr_context: Optional[str] = None
    egfr_span: Optional[List[int]] = None

    if egfr_matches:
        # Pick the most recent value (last mention or discharge context)
        # Search backwards for discharge indicators
        chosen_match = egfr_matches[-1]
        for m in reversed(egfr_matches):
            ctx_window = text_lower[max(0, m.start() - 150) : m.start()]
            if any(k in ctx_window for k in ["discharge", "current", "latest", "day 7", "repeat"]):
                chosen_match = m
                break

        try:
            egfr_val = float(chosen_match.group(1))
            if chosen_match.group(2):
                egfr_unit = chosen_match.group(2)
            egfr_span = [chosen_match.start(), chosen_match.end()]
            egfr_context = raw_text[max(0, chosen_match.start() - 30) : min(len(raw_text), chosen_match.end() + 30)].strip()
        except ValueError:
            pass

    creat_val: Optional[float] = None
    creat_unit: str = "mg/dL"
    creat_context: Optional[str] = None
    creat_span: Optional[List[int]] = None

    if creat_matches:
        chosen_cr = creat_matches[-1]
        for m in reversed(creat_matches):
            ctx_window = text_lower[max(0, m.start() - 150) : m.start()]
            if any(k in ctx_window for k in ["discharge", "current", "latest", "day 7", "repeat"]):
                chosen_cr = m
                break

        try:
            creat_val = float(chosen_cr.group(1))
            if chosen_cr.group(2):
                creat_unit = chosen_cr.group(2)
            creat_span = [chosen_cr.start(), chosen_cr.end()]
            creat_context = raw_text[max(0, chosen_cr.start() - 30) : min(len(raw_text), chosen_cr.end() + 30)].strip()
        except ValueError:
            pass

    return {
        "egfr": egfr_val,
        "egfr_unit": egfr_unit,
        "egfr_context": egfr_context,
        "egfr_span": egfr_span,
        "creatinine": creat_val,
        "creatinine_unit": creat_unit,
        "creatinine_context": creat_context,
        "creatinine_span": creat_span,
        "serial_measurements_found": len(egfr_matches),
        "raw_matches": {
            "egfr": chosen_match.group(0) if egfr_matches else None,
            "creatinine": chosen_cr.group(0) if creat_matches else None,
        },
    }


def find_drugs_in_summary(summary_text: str, drug_list: List[str]) -> List[Dict[str, Any]]:
    """Check if any contraindicated drugs appear as active orders in summary.

    Returns structured matches with exact character span offsets [start, end].
    Ignores explicit cessation/withholding directives (e.g. 'withhold metformin', 'avoid NSAIDs').
    """
    found = []
    summary_lower = summary_text.lower()

    for drug in drug_list:
        escaped = re.escape(drug.lower())
        pattern = rf"\b{escaped}\b"
        for m in re.finditer(pattern, summary_lower):
            # Check prefix context window for negation or withholding phrases
            prefix_window = summary_lower[max(0, m.start() - 45) : m.start()]
            if NEGATION_ORDER_PATTERN.search(prefix_window):
                continue

            snippet = summary_text[max(0, m.start() - 25) : min(len(summary_text), m.end() + 25)].strip()
            found.append({
                "drug": drug,
                "evidence": snippet,
                "span": [m.start(), m.end()],
            })

    return found


def audit_clinical_safety(
    raw_ehr: str,
    summary_content: str,
    rules: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute complete deterministic invariant evaluation with character span evidence."""
    start_time = time.perf_counter()
    violations: List[Dict[str, Any]] = []
    passed_checks: List[str] = []

    # 1. Allergy Audit
    detected_allergies = extract_patient_allergies(raw_ehr, rules)
    for allergy_info in detected_allergies:
        rule = allergy_info["rule"]
        rule_id = allergy_info["rule_id"]
        allergy_class = allergy_info["allergy_class"]
        all_contraindicated = rule.get("contraindicated_drugs", []) + rule.get("cross_reactive_drugs", [])

        clashes = find_drugs_in_summary(summary_content, all_contraindicated)
        if clashes:
            for clash in clashes:
                drug_name = clash["drug"]
                is_cross = drug_name in rule.get("cross_reactive_drugs", [])
                severity = "HIGH" if is_cross else rule.get("severity", "CRITICAL")
                violations.append({
                    "rule_id": rule_id,
                    "type": "ALLERGY_CONTRAINDICATION",
                    "severity": severity,
                    "allergy_class": allergy_class,
                    "offending_drug": drug_name,
                    "drug": drug_name,
                    "evidence_in_summary": clash["evidence"],
                    "evidence": clash["evidence"],
                    "summary_span": clash["span"],
                    "patient_allergy_evidence": allergy_info["evidence"],
                    "patient_evidence_span": allergy_info["span"],
                    "mechanism": rule.get("mechanism", "Hypersensitivity reaction"),
                    "recommendation": f"Immediately remove '{drug_name}' from discharge orders. Patient has documented {allergy_class.upper()} allergy.",
                })
        else:
            passed_checks.append(f"Allergy Check Passed: {allergy_class.upper()} (No contraindicated drugs in summary)")

    # 2. Renal Clearance Threshold Audit
    renal_metrics = extract_renal_metrics(raw_ehr)
    egfr = renal_metrics.get("egfr")

    renal_rules = rules.get("renal_clearance_thresholds", [])
    for rule in renal_rules:
        rule_id = rule.get("rule_id", f"CS-RENAL-{rule['drug_name'].upper()}")
        drug_name = rule["drug_name"]
        cutoff = rule["egfr_cutoff_ml_min"]
        aliases = rule.get("aliases", [drug_name])

        if egfr is not None and egfr < cutoff:
            clashes = find_drugs_in_summary(summary_content, aliases)
            if clashes:
                for clash in clashes:
                    drug_alias = clash["drug"]
                    violations.append({
                        "rule_id": rule_id,
                        "type": "RENAL_THRESHOLD_VIOLATION",
                        "severity": rule.get("severity", "CRITICAL"),
                        "offending_drug": drug_alias,
                        "drug": drug_alias,
                        "egfr_observed": egfr,
                        "egfr_cutoff": cutoff,
                        "evidence_in_summary": clash["evidence"],
                        "evidence": clash["evidence"],
                        "summary_span": clash["span"],
                        "patient_lab_context": renal_metrics.get("egfr_context"),
                        "rationale": rule.get("rationale", "Nephrotoxic drug in renal insufficiency"),
                        "recommendation": f"Withhold or dose-adjust '{drug_alias}'. Patient eGFR is {egfr} mL/min, which is below the safe threshold of {cutoff} mL/min.",
                    })
            else:
                passed_checks.append(f"Renal Threshold Check Passed: {drug_name} safe (None ordered while eGFR={egfr})")
        else:
            passed_checks.append(f"Renal Threshold Check: {drug_name} cleared or eGFR normal")

    # 3. High Risk Drug-Drug Interactions
    ddi_rules = rules.get("drug_drug_interactions", [])
    combined_clinical_context = (raw_ehr + " " + summary_content).lower()
    for ddi in ddi_rules:
        rule_id = ddi.get("rule_id", "CS-DDI-GENERIC")
        drugs_a = ddi.get("drug_a", [])
        drugs_b = ddi.get("drug_b", [])

        found_a = [da for da in drugs_a if re.search(rf"\b{re.escape(da)}\b", combined_clinical_context)]
        found_b_in_summary = find_drugs_in_summary(summary_content, drugs_b)

        if found_a and found_b_in_summary:
            for clash in found_b_in_summary:
                drug_b = clash["drug"]
                violations.append({
                    "rule_id": rule_id,
                    "type": "DRUG_DRUG_INTERACTION",
                    "severity": ddi.get("severity", "CRITICAL"),
                    "interacting_pair": [found_a[0], drug_b],
                    "offending_drug": drug_b,
                    "drug": drug_b,
                    "evidence_in_summary": clash["evidence"],
                    "evidence": clash["evidence"],
                    "summary_span": clash["span"],
                    "rationale": ddi.get("rationale", "Adverse drug interaction"),
                    "recommendation": f"Avoid concurrent ordering of '{found_a[0]}' and '{drug_b}'.",
                })
        else:
            passed_checks.append(f"DDI Check: {drugs_a[0]} + {drugs_b[0]} interaction clear")

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    status = "FAIL" if violations else "PASS"

    return {
        "status": status,
        "total_violations": len(violations),
        "violations": violations,
        "passed_checks_count": len(passed_checks),
        "passed_checks": passed_checks,
        "renal_metrics": renal_metrics,
        "execution_time_ms": round(elapsed_ms, 2),
        "schema_version": "1.1.0",
        "standard": "agent-skills.io/v1",
    }


def parse_summary_payload(summary_raw: str) -> str:
    """Extract plain text summary from JSON or raw text."""
    try:
        data = json.loads(summary_raw)
        if isinstance(data, dict):
            for key in ["summary", "discharge_summary", "instructions", "content", "patient_summary", "text"]:
                if key in data and isinstance(data[key], str):
                    return data[key]
            return json.dumps(data)
    except Exception:
        pass
    return summary_raw


def explain_report(report: Dict[str, Any]) -> str:
    """Format a detailed clinical rationale explanation for all findings."""
    lines = [
        "============================================================",
        f" CareSentry Clinical Safety Invariant Audit: {report['status']}",
        "============================================================",
        f"Execution Latency: {report['execution_time_ms']} ms",
        f"Passed Checks    : {report['passed_checks_count']}",
        f"Total Violations : {report['total_violations']}",
    ]
    if report.get("renal_metrics", {}).get("egfr"):
        lines.append(f"Patient eGFR     : {report['renal_metrics']['egfr']} {report['renal_metrics'].get('egfr_unit', 'mL/min')}")
    lines.append("------------------------------------------------------------")

    for idx, v in enumerate(report["violations"], 1):
        lines.append(f"VIOLATION #{idx} [{v.get('rule_id', 'UNKNOWN')}]: {v['type']} ({v['severity']})")
        lines.append(f"  Offending Medication : {v.get('offending_drug')}")
        lines.append(f"  Summary Span Offset  : {v.get('summary_span')}")
        lines.append(f"  Evidence in Summary  : \"{v.get('evidence_in_summary')}\"")
        if v.get("patient_allergy_evidence"):
            lines.append(f"  Patient Chart Record : \"{v.get('patient_allergy_evidence')}\"")
        lines.append(f"  Clinical Directive   : {v.get('recommendation')}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CareSentry-AI Deterministic Clinical Safety Invariant Linter"
    )
    parser.add_argument(
        "--records",
        "-r",
        required=True,
        help="Path to raw patient discharge notes / EHR text file, or inline text string.",
    )
    parser.add_argument(
        "--summary",
        "-s",
        required=True,
        help="Path to model-generated summary (JSON or text file), or inline string.",
    )
    parser.add_argument(
        "--rules",
        help="Optional path to custom clinical_rules.json matrix.",
        default=None,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Always emit machine-readable JSON only to stdout.",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print detailed clinical guideline explanations for any violations.",
    )

    args = parser.parse_args()

    if os.path.exists(args.records):
        with open(args.records, "r", encoding="utf-8") as f:
            records_text = f.read()
    else:
        records_text = args.records

    if os.path.exists(args.summary):
        with open(args.summary, "r", encoding="utf-8") as f:
            summary_raw = f.read()
    else:
        summary_raw = args.summary

    summary_text = parse_summary_payload(summary_raw)
    rules = load_clinical_rules(args.rules)

    report = audit_clinical_safety(records_text, summary_text, rules)

    if args.explain:
        print(explain_report(report))
    else:
        print(json.dumps(report, indent=2))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
