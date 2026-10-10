"""CareSentry-AI Deterministic Clinical Invariant Linter.

Evaluates raw patient discharge records / EHRs against generated summaries
for drug-allergy clashes, renal threshold contraindications (e.g. eGFR < 30),
and high-risk drug-drug interactions with sub-100ms offline latency.

Complies with Agent Skill Open Standard (agentskills.io/v1).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_clinical_rules(rules_path: Optional[str] = None) -> Dict[str, Any]:
    """Load deterministic clinical rule matrix."""
    if rules_path and os.path.exists(rules_path):
        target = Path(rules_path)
    else:
        # Search relative to repo root / standard paths
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
            raise FileNotFoundError(
                "Could not locate clinical_rules.json in standard reference paths."
            )

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_patient_allergies(raw_text: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scan raw clinical text for documented drug allergies."""
    detected = []
    text_lower = raw_text.lower()

    allergy_rules = rules.get("allergies", [])
    for rule in allergy_rules:
        allergy_class = rule["allergy_class"]
        aliases = rule.get("aliases", [allergy_class])

        for alias in aliases:
            escaped = re.escape(alias.lower())
            patterns = [
                rf"(?:allerg(?:y|ies|ic)\s*(?:to|:)?\s*[\w\s,;-]{{0,30}}?\b{escaped}\b)",
                rf"\b{escaped}\b(?:\s+\w+){{0,2}}\s*(?:allergy|anaphylaxis|hypersensitivity|reaction|intolerance)",
                rf"(?:adverse\s+reaction\s+to\s+[\w\s,;-]{{0,20}}?\b{escaped}\b)",
            ]
            matched = False
            for pat in patterns:
                m = re.search(pat, text_lower)
                if m:
                    snippet = raw_text[max(0, m.start() - 20) : min(len(raw_text), m.end() + 20)].strip()
                    detected.append({
                        "allergy_class": allergy_class,
                        "matched_alias": alias,
                        "evidence": snippet,
                        "rule": rule,
                    })
                    matched = True
                    break
            if matched:
                break

    return detected


def extract_renal_metrics(raw_text: str) -> Dict[str, Any]:
    """Extract eGFR and Creatinine lab measurements from clinical records."""
    text_lower = raw_text.lower()

    egfr_match = re.search(
        r"(?:egfr|gfr|estimated\s+gfr|est\.?\s*gfr)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,3}(?:\.[0-9]+)?)",
        text_lower,
    )

    creatinine_match = re.search(
        r"(?:creatinine|serum\s+creatinine|creat)\s*(?:=|:|\bof\b|\bis\b)?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
        text_lower,
    )

    egfr_val: Optional[float] = None
    if egfr_match:
        try:
            egfr_val = float(egfr_match.group(1))
        except ValueError:
            pass

    creat_val: Optional[float] = None
    if creatinine_match:
        try:
            creat_val = float(creatinine_match.group(1))
        except ValueError:
            pass

    return {
        "egfr": egfr_val,
        "creatinine": creat_val,
        "raw_matches": {
            "egfr": egfr_match.group(0) if egfr_match else None,
            "creatinine": creatinine_match.group(0) if creatinine_match else None,
        },
    }


NEGATION_PATTERN = re.compile(
    r"\b(withhold|hold|stop|discontinue|avoid|cease|do\s+not\s+(?:give|order|prescribe|administer)|no\s+|contraindicated|prohibited)\b",
    re.IGNORECASE,
)


def find_drugs_in_summary(summary_text: str, drug_list: List[str]) -> List[Tuple[str, str]]:
    """Check if any contraindicated drugs appear as active orders in summary.

    Ignores explicit cessation/withholding directives (e.g. 'withhold metformin', 'avoid NSAIDs').
    """
    found = []
    summary_lower = summary_text.lower()

    for drug in drug_list:
        escaped = re.escape(drug.lower())
        pattern = rf"\b{escaped}\b"
        for m in re.finditer(pattern, summary_lower):
            # Check prefix context (up to 45 chars before drug) for cessation/withholding directives
            prefix_window = summary_lower[max(0, m.start() - 45) : m.start()]
            if NEGATION_PATTERN.search(prefix_window):
                # Drug is explicitly being withheld or avoided
                continue

            snippet = summary_text[max(0, m.start() - 25) : min(len(summary_text), m.end() + 25)].strip()
            found.append((drug, snippet))

    return found


def audit_clinical_safety(
    raw_ehr: str,
    summary_content: str,
    rules: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute complete deterministic invariant evaluation."""
    start_time = time.perf_counter()
    violations: List[Dict[str, Any]] = []
    passed_checks: List[str] = []

    # 1. Allergy Audit
    detected_allergies = extract_patient_allergies(raw_ehr, rules)
    for allergy_info in detected_allergies:
        rule = allergy_info["rule"]
        allergy_class = allergy_info["allergy_class"]
        all_contraindicated = rule.get("contraindicated_drugs", []) + rule.get("cross_reactive_drugs", [])

        clashes = find_drugs_in_summary(summary_content, all_contraindicated)
        if clashes:
            for drug_name, snippet in clashes:
                is_cross = drug_name in rule.get("cross_reactive_drugs", [])
                severity = "HIGH" if is_cross else rule.get("severity", "CRITICAL")
                violations.append({
                    "type": "ALLERGY_CONTRAINDICATION",
                    "severity": severity,
                    "allergy_class": allergy_class,
                    "offending_drug": drug_name,
                    "evidence_in_summary": snippet,
                    "patient_allergy_evidence": allergy_info["evidence"],
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
        drug_name = rule["drug_name"]
        cutoff = rule["egfr_cutoff_ml_min"]
        aliases = rule.get("aliases", [drug_name])

        if egfr is not None and egfr < cutoff:
            clashes = find_drugs_in_summary(summary_content, aliases)
            if clashes:
                for drug_alias, snippet in clashes:
                    violations.append({
                        "type": "RENAL_THRESHOLD_VIOLATION",
                        "severity": rule.get("severity", "CRITICAL"),
                        "offending_drug": drug_alias,
                        "egfr_observed": egfr,
                        "egfr_cutoff": cutoff,
                        "evidence_in_summary": snippet,
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
        drugs_a = ddi.get("drug_a", [])
        drugs_b = ddi.get("drug_b", [])

        found_a = [da for da in drugs_a if re.search(rf"\b{re.escape(da)}\b", combined_clinical_context)]
        found_b_in_summary = find_drugs_in_summary(summary_content, drugs_b)

        if found_a and found_b_in_summary:
            for drug_b, snippet in found_b_in_summary:
                violations.append({
                    "type": "DRUG_DRUG_INTERACTION",
                    "severity": ddi.get("severity", "CRITICAL"),
                    "interacting_pair": [found_a[0], drug_b],
                    "evidence_in_summary": snippet,
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

    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
