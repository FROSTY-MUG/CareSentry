"""Dose-aware renal function calculations.

Implements standard clinical formulas:
1. Cockcroft-Gault Creatinine Clearance (CrCl, mL/min)
2. CKD-EPI (2021 race-free) Estimated Glomerular Filtration Rate (eGFR, mL/min/1.73m2)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple


def calculate_cockcroft_gault_crcl(
    serum_creatinine: float,
    age: int,
    weight_kg: float,
    is_female: bool,
) -> Optional[float]:
    """Calculate Creatinine Clearance using the Cockcroft-Gault equation.
    
    CrCl (mL/min) = [ (140 - age) * weight_kg ] / [ 72 * Scr (mg/dL) ] * (0.85 if female else 1.00)
    """
    if serum_creatinine <= 0.0 or age <= 0 or weight_kg <= 0.0:
        return None

    numerator = (140.0 - float(age)) * float(weight_kg)
    denominator = 72.0 * float(serum_creatinine)
    crcl = (numerator / denominator) * (0.85 if is_female else 1.0)
    return round(crcl, 1)


def calculate_ckd_epi_2021_egfr(
    serum_creatinine: float,
    age: int,
    is_female: bool,
) -> Optional[float]:
    """Calculate eGFR using the 2021 CKD-EPI race-free equation (Inker et al., NEJM 2021).
    
    eGFR = 142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200) * 0.9938^age * (1.012 if female)
    """
    if serum_creatinine <= 0.0 or age <= 0:
        return None

    kappa = 0.7 if is_female else 0.9
    alpha = -0.241 if is_female else -0.302
    gender_factor = 1.012 if is_female else 1.0

    scr_over_kappa = serum_creatinine / kappa
    min_factor = math.pow(min(scr_over_kappa, 1.0), alpha)
    max_factor = math.pow(max(scr_over_kappa, 1.0), -1.200)
    age_factor = math.pow(0.9938, float(age))

    egfr = 142.0 * min_factor * max_factor * age_factor * gender_factor
    return round(egfr, 1)


def resolve_effective_renal_clearance(
    stated_egfr: Optional[float],
    serum_creatinine: Optional[float],
    age: Optional[int],
    weight_kg: Optional[float],
    is_female: Optional[bool],
) -> Tuple[Optional[float], Optional[float], str]:
    """Determine effective renal metrics.
    
    Returns:
        (effective_egfr, effective_crcl, calculation_method)
    """
    crcl: Optional[float] = None
    if serum_creatinine and age and weight_kg is not None and is_female is not None:
        crcl = calculate_cockcroft_gault_crcl(serum_creatinine, age, weight_kg, is_female)

    if stated_egfr is not None:
        return stated_egfr, crcl, "STATED_EHR_EGFR"

    if serum_creatinine and age and is_female is not None:
        computed_egfr = calculate_ckd_epi_2021_egfr(serum_creatinine, age, is_female)
        return computed_egfr, crcl, "COMPUTED_CKD_EPI_2021"

    return None, crcl, "INSUFFICIENT_DATA"
