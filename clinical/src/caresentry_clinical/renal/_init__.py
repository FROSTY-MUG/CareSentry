"""Renal function calculation module for CareSentry Clinical.

Implements Cockcroft-Gault CrCl and CKD-EPI 2021 eGFR from
creatinine, age, sex, weight, and race. Formulas sourced from
clinical/references/renal_calculations.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

# Base path for source files
_SOURCES_DIR = Path(__file__).parent.parent.parent / "sources"


class CrclResult(NamedTuple):
    """Cockcroft-Gault Creatinine Clearance result."""
    crcl_ml_min: float
    age: int
    sex: str  # "male" or "female"
    weight_kg: float
    creatinine_mg_dL: float
    formula_name: str = "Cockcroft-Gault"


class EgfrResult(NamedTuple):
    """CKD-EPI 2021 eGFR result."""
    egfr_ml_min_173m2: float
    age: int
    sex: str  # "male" or "female"
    race: str  # "Black" or "non-Black"
    creatinine_mg_dL: float
    formula_name: str = "CKD-EPI 2021"


class RenalThresholds(NamedTuple):
    """Renal thresholds per drug."""
    metformin_egfr_cutoff_ml_min: int = 30
    spironolactone_egfr_cutoff_ml_min: int = 30
    nsaid_egfr_cutoff_ml_min: int = 30


def _load_formulas() -> Dict[str, Any]:
    """Load renal calculation formulas from source file."""
    filepath = _SOURCES_DIR / "renal_calculations.json"
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_cockcroft_gault(
    age: int,
    sex: str,
    weight_kg: float,
    creatinine_mg_dL: float,
) -> CrclResult:
    """Calculate Cockcroft-Gault Creatinine Clearance (CrCl).

    CrCl = (140 - age) * weight / (72 * creatinine) * (0.85 if female)

    Args:
        age: Patient age in years
        sex: "male" or "female"
        weight_kg: Body weight in kilograms
        creatinine_mg_dL: Serum creatinine in mg/dL

    Returns:
        CrclResult with calculated CrCl in mL/min
    """
    formulas = _load_formulas()
    kg_coeff = 0.85 if sex.lower() == "female" else 1.0
    crcl = (140 - age) * weight_kg / (72 * creatinine_mg_dL) * kg_coeff
    return CrclResult(
        crcl_ml_min=round(crcl, 1),
        age=age,
        sex=sex,
        weight_kg=weight_kg,
        creatinine_mg_dL=creatinine_mg_dL,
        formula_name=formulas["formulas"]["cockcroft_gault"]["equation"],
    )


def calculate_ckd_epi_2021(
    age: int,
    sex: str,
    race: str,
    creatinine_mg_dL: float,
) -> EgfrResult:
    """Calculate CKD-EPI 2021 eGFR (race-free).

    Uses race-free coefficients per current guidelines.

    Args:
        age: Patient age in years
        sex: "male" or "female"
        race: "Black" or "non-Black" (race-free version uses same coefficients)
        creatinine_mg_dL: Serum creatinine in mg/dL

    Returns:
        EgfrResult with eGFR in mL/min/1.73m2
    """
    formulas = _load_formulas()

    # CKD-EPI 2021 race-free coefficients
    if sex.lower() == "female":
        k = 0.7
        a = -0.241
    else:
        k = 0.9
        a = -0.202

    # Calculate eGFR
    scr = creatinine_mg_dL
    min_scr_k = min(scr / k, 1)
    max_scr_k = max(scr / k, 1)

    egfr = 142 * (min_scr_k ** a) * (max_scr_k ** -1.200)

    # Apply sex and race factors (race-free: no Black race multiplier)
    if sex.lower() == "female":
        egfr *= 1.012
    # Race-free: no 1.159 Black factor

    return EgfrResult(
        egfr_ml_min_173m2=round(egfr, 1),
        age=age,
        sex=sex,
        race=race,
        creatinine_mg_dL=creatinine_mg_dL,
        formula_name=formulas["formulas"]["ckd_epi_2021"]["equation"],
    )


def get_renal_thresholds() -> RenalThresholds:
    """Get renal action thresholds per drug from source file."""
    formulas = _load_formulas()
    thresholds_data = formulas["renal_thresholds"]
    return RenalThresholds(
        metformin_egfr_cutoff_ml_min=data.get("metformin_egfr_cutoff_ml_min", 30),
        spironolactone_egfr_cutoff_ml_min=data.get("spironolactone_egfr_cutoff_ml_min", 30),
        nsaid_egfr_cutoff_ml_min=data.get("nsaid_egfr_cutoff_ml_min", 30),
    )


def check_renal_threshold(
    drug_name: str,
    egfr_or_crcl: float,
    thresholds: Optional[RenalThresholds] = None,
) -> Dict[str, Any]:
    """Check if a drug is contraindicated based on renal function.

    Args:
        drug_name: Name of the drug to check
        egfr_or_crcl: eGFR (mL/min/1.73m2) or CrCl (mL/min) value
        thresholds: RenalThresholds instance (uses defaults if None)

    Returns:
        Dict with contraindication status and rationale
    """
    if thresholds is None:
        thresholds = get_renal_thresholds()

    drug_lower = drug_name.lower()

    # Metformin check
    if "metformin" in drug_lower:
        if egfr_or_crcl < thresholds.metformin_egfr_cutoff_ml_min:
            return {
                "contraindicated": True,
                "drug": drug_name,
                "threshold": thresholds.metformin_egfr_cutoff_ml_min,
                "observed": egfr_or_crcl,
                "action": "Withhold metformin; consider alternative antidiabetic",
                "rationale": "High risk of life-threatening metformin-associated "
                             "lactic acidosis (MALA) when eGFR < 30 mL/min/1.73m²",
            }

    # Spironolactone check
    if "spironolactone" in drug_lower:
        if egfr_or_crcl < thresholds.spironolactone_egfr_cutoff_ml_min:
            return {
                "contraindicated": True,
                "drug": drug_name,
                "threshold": thresholds.spironolactone_egfr_cutoff_ml_min,
                "observed": egfr_or_crcl,
                "action": "Withhold spironolactone; monitor potassium and renal function",
                "rationale": "Severe risk of fatal hyperkalemia and acute kidney "
                             "injury worsening in advanced renal impairment",
            }

    # NSAIDs check
    if any(x in drug_lower for x in ["nsaid", "ibuprofen", "naproxen", "diclofenac"]):
        if egfr_or_crcl < thresholds.nsaid_egfr_cutoff_ml_min:
            return {
                "contraindicated": True,
                "drug": drug_name,
                "threshold": thresholds.nsaid_egfr_cutoff_ml_min,
                "observed": egfr_or_crcl,
                "action": "Avoid NSAIDs; use alternative pain agent",
                "rationale": "Inhibits renal prostaglandin synthesis, causing "
                             "afferent arteriolar vasoconstriction and "
                             "precipitating acute-on-chronic renal failure",
            }

    return {
        "contraindicated": False,
        "drug": drug_name,
        "threshold": None,
        "observed": egfr_or_crcl,
        "action": "No renal threshold violation",
        "rationale": "Renal function is above the contraindication threshold",
    }


# Create module-level instances for convenience
_default_thresholds = None


def get_default_thresholds() -> RenalThresholds:
    """Get the default renal thresholds (cached)."""
    global _default_thresholds
    if _default_thresholds is None:
        _default_thresholds = get_renal_thresholds()
    return _default_thresholds


# Convenience functions
def calculate_crcl(
    age: int,
    sex: str,
    weight_kg: float,
    creatinine_mg_dL: float,
) -> CrclResult:
    """Quick function to calculate CrCl."""
    return calculate_cockcroft_gault(age, sex, weight_kg, creatinine_mg_dL)


def calculate_egfr(
    age: int,
    sex: str,
    race: str,
    creatinine_mg_dL: float,
) -> EgfrResult:
    """Quick function to calculate eGFR."""
    return calculate_ckd_epi_2021(age, sex, race, creatinine_mg_dL)


def check_renal(
    drug_name: str,
    egfr_or_crcl: float,
    thresholds: Optional[RenalThresholds] = None,
) -> Dict[str, Any]:
    """Quick function to check renal contraindication."""
    return check_renal_threshold(drug_name, egfr_or_crcl, thresholds)