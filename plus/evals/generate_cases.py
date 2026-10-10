"""Templated Large-Scale Synthetic Case Generator (F-05).

Generates >= 100 realistic synthetic EHR notes and discharge summaries varying
needle depth, clinical distractors, abbreviations, and invariant categories.
Strictly deterministic with a fixed random seed (42). Does not touch Track A data.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

SEED = 42
DATA_PLUS_DIR = Path(__file__).resolve().parent.parent / "data_plus"
OUTPUT_FILE = DATA_PLUS_DIR / "synthetic_cases.json"

CLINICAL_DISTRACTORS = [
    "Vital signs upon presentation: BP 128/78 mmHg, HR 74 bpm, RR 16 bpm, SpO2 98% on room air.",
    "Past surgical history notable for laparoscopic appendectomy in 2012 without anesthesia complications.",
    "Chest X-ray demonstrated clear lung fields bilaterally with no focal consolidation or pleural effusion.",
    "Comprehensive metabolic panel: Sodium 139 mEq/L, Chloride 102 mEq/L, Bicarbonate 24 mEq/L, Glucose 104 mg/dL.",
    "Complete blood count: WBC 6.8 x10^3/uL, Hemoglobin 13.5 g/dL, Hematocrit 40.2%, Platelets 220 x10^3/uL.",
    "Social history: Non-smoker, drinks occasional glass of wine on weekends, works as an accountant.",
    "Electrocardiogram displayed normal sinus rhythm at 72 bpm with normal PR and QTc intervals.",
    "Physical examination: Alert and oriented x4, cardiovascular regular rate and rhythm, abdomen soft and non-tender.",
    "Patient ambulated in hallways with physical therapy, demonstrating steady gait and baseline endurance.",
    "Patient verbalized good understanding of diet recommendations and scheduled outpatient follow-up."
]

TEMPLATES = [
    # 1. Penicillin allergy + Cephalosporin order (Cross-reactivity)
    {
        "category": "cross_reactivity",
        "needle_template": "DOCUMENTED ALLERGY: Patient has severe {allergy_name} allergy resulting in urticaria and facial angioedema.",
        "order_template": "Prescribed {order_drug} 500 mg PO TID for wound cellulitis.",
        "allergy_options": ["Penicillin", "Amoxicillin", "PCN", "Augmentin"],
        "order_options": ["Cephalexin", "Keflex", "Cefazolin"],
        "expected_rule": "PLUS-CROSS-01",
        "is_violation": True,
        "is_omission": True,
    },
    # 2. Sulfa allergy + Sulfa antibiotic (Cross-reactivity)
    {
        "category": "cross_reactivity",
        "needle_template": "ALLERGIES: Confirmed severe allergy to {allergy_name} with diffuse cutaneous exanthem.",
        "order_template": "Discharge medication: {order_drug} 500 mg daily.",
        "allergy_options": ["Bactrim", "Septra", "Sulfamethoxazole", "TMP-SMX"],
        "order_options": ["Sulfadiazine", "Sulfasalazine"],
        "expected_rule": "PLUS-CROSS-02",
        "is_violation": True,
        "is_omission": True,
    },
    # 3. Aspirin allergy + NSAID order (Cross-reactivity)
    {
        "category": "cross_reactivity",
        "needle_template": "CRITICAL ALERT: Patient diagnosed with Aspirin-exacerbated respiratory disease ({allergy_name} allergy).",
        "order_template": "Initiated {order_drug} 400 mg every 6 hours PRN acute musculoskeletal pain.",
        "allergy_options": ["Aspirin", "ASA", "acetylsalicylic acid"],
        "order_options": ["Ibuprofen", "Naproxen", "Toradol", "Ketorolac", "Meloxicam"],
        "expected_rule": "PLUS-CROSS-03",
        "is_violation": True,
        "is_omission": True,
    },
    # 4. Severe Renal Impairment + Metformin
    {
        "category": "dose_aware_renal",
        "needle_template": "LABS: Baseline Serum Creatinine 3.2 mg/dL, estimated GFR (eGFR) is {renal_metric} mL/min/1.73m2.",
        "order_template": "Continue home oral antidiabetic therapy with {order_drug} 1000 mg BID with meals.",
        "renal_metric_options": ["18", "22", "26", "24"],
        "order_options": ["Metformin", "Glucophage", "Janumet"],
        "expected_rule": "PLUS-RENAL-01",
        "is_violation": True,
        "is_omission": True,
    },
    # 5. Severe Renal Impairment + Spironolactone
    {
        "category": "dose_aware_renal",
        "needle_template": "RENAL PROFILE: Chronic Kidney Disease with observed eGFR of {renal_metric} mL/min.",
        "order_template": "Discharge prescription includes {order_drug} 25 mg daily for heart failure.",
        "renal_metric_options": ["20", "25", "19", "23"],
        "order_options": ["Spironolactone", "Aldactone"],
        "expected_rule": "PLUS-RENAL-02",
        "is_violation": True,
        "is_omission": True,
    },
    # 6. Geriatric Beers Criteria (Antihistamines)
    {
        "category": "geriatric_beers",
        "needle_template": "PATIENT PROFILE: Patient is an elderly {age}-year-old female admitted for dehydration.",
        "order_template": "Nightly sleep aid: {order_drug} 50 mg PO at bedtime PRN insomnia.",
        "age_options": ["72", "78", "84", "89"],
        "order_options": ["Diphenhydramine", "Benadryl", "Hydroxyzine", "Atarax"],
        "expected_rule": "PLUS-BEERS-01",
        "is_violation": True,
        "is_omission": False,
    },
    # 7. Geriatric Beers Criteria (Tricyclic Antidepressants)
    {
        "category": "geriatric_beers",
        "needle_template": "DEMOGRAPHICS: {age}-year-old male with history of diabetic peripheral neuropathy.",
        "order_template": "Prescribed {order_drug} 25 mg at bedtime for neuropathic discomfort.",
        "age_options": ["68", "74", "81"],
        "order_options": ["Amitriptyline", "Elavil"],
        "expected_rule": "PLUS-BEERS-02",
        "is_violation": True,
        "is_omission": False,
    },
    # 8. High-Risk DDI: Warfarin + NSAID
    {
        "category": "drug_drug_interaction",
        "needle_template": "CURRENT MEDICATIONS: Therapeutic oral anticoagulation with {drug_a} 5 mg daily for chronic atrial fibrillation.",
        "order_template": "Discharge medications include {drug_b} 500 mg BID for osteoarthritis pain.",
        "drug_a_options": ["Warfarin", "Coumadin"],
        "drug_b_options": ["Naproxen", "Ibuprofen", "Meloxicam"],
        "expected_rule": "PLUS-DDI-01",
        "is_violation": True,
        "is_omission": True,
    },
    # 9. Clean Negative Control (Safe Tolerated Medication)
    {
        "category": "negative_control",
        "needle_template": "Patient has no known drug allergies (NKDA). Renal function normal with eGFR 85 mL/min.",
        "order_template": "Discharge orders: Acetaminophen 650 mg PO Q6H PRN pain and Lisinopril 10 mg daily.",
        "expected_rule": None,
        "is_violation": False,
        "is_omission": False,
    },
    # 10. Clean Negative Control (Historical tolerance)
    {
        "category": "negative_control",
        "needle_template": "Patient tolerated Amoxicillin in 2021 without adverse reaction. Normal kidney labs.",
        "order_template": "Discharged on Cephalexin 500 mg PO QID for 7 days.",
        "expected_rule": None,
        "is_violation": False,
        "is_omission": False,
    }
]


def generate_synthetic_cases(count: int = 120, seed: int = SEED) -> List[Dict[str, Any]]:
    """Generate deterministic synthetic test cases."""
    rng = random.Random(seed)
    cases = []

    depth_targets = [0.15, 0.50, 0.85]  # early, middle, late

    for idx in range(1, count + 1):
        tmpl = rng.choice(TEMPLATES)
        cat = tmpl["category"]
        depth = depth_targets[idx % len(depth_targets)]

        # Build needle
        if cat == "cross_reactivity":
            allergy = rng.choice(tmpl["allergy_options"])
            order_drug = rng.choice(tmpl["order_options"])
            needle = tmpl["needle_template"].format(allergy_name=allergy)
            summary = f"Patient discharge summary. {tmpl['order_template'].format(order_drug=order_drug)}"
        elif cat == "dose_aware_renal":
            renal = rng.choice(tmpl["renal_metric_options"])
            order_drug = rng.choice(tmpl["order_options"])
            needle = tmpl["needle_template"].format(renal_metric=renal)
            summary = f"Hospital Course Summary. {tmpl['order_template'].format(order_drug=order_drug)}"
        elif cat == "geriatric_beers":
            age = rng.choice(tmpl["age_options"])
            order_drug = rng.choice(tmpl["order_options"])
            needle = tmpl["needle_template"].format(age=age)
            summary = f"Discharge Instructions. {tmpl['order_template'].format(order_drug=order_drug)}"
        elif cat == "drug_drug_interaction":
            drug_a = rng.choice(tmpl["drug_a_options"])
            drug_b = rng.choice(tmpl["drug_b_options"])
            needle = tmpl["needle_template"].format(drug_a=drug_a)
            summary = f"Discharge Medication Plan. {tmpl['order_template'].format(drug_b=drug_b)}"
        else:  # negative_control
            needle = tmpl["needle_template"]
            summary = tmpl["order_template"]

        # Insert distractors around needle based on target depth
        total_distractors = 14
        num_before = int(total_distractors * depth)
        num_after = total_distractors - num_before

        before_paras = [rng.choice(CLINICAL_DISTRACTORS) for _ in range(num_before)]
        after_paras = [rng.choice(CLINICAL_DISTRACTORS) for _ in range(num_after)]

        record_parts = before_paras + [f"[CRITICAL CLINICAL OBSERVATION]: {needle}"] + after_paras
        full_record = "\n\n".join(record_parts)

        case = {
            "case_id": f"PLUS-CASE-{idx:03d}",
            "category": cat,
            "target_depth_fraction": depth,
            "needle_text": needle,
            "patient_record": full_record,
            "discharge_summary": summary,
            "is_violation": tmpl["is_violation"],
            "is_omission": tmpl["is_omission"],
            "expected_rule_id": tmpl["expected_rule"],
        }
        cases.append(case)

    return cases


def main() -> None:
    cases = generate_synthetic_cases(count=120, seed=SEED)
    DATA_PLUS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Successfully generated {len(cases)} deterministic cases in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
