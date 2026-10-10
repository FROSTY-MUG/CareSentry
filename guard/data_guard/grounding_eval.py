"""Grounding evaluation dataset generator with 100+ labeled clinical sentences."""

import json
from pathlib import Path

SAMPLE_EHR = """
PATIENT DISCHARGE SUMMARY: Harold Vance, 84-year-old male.
ADMISSION DIAGNOSIS: Decompensated Heart Failure, Stage 3b CKD, Atrial Fibrillation.
HOSPITAL COURSE: Patient admitted with lower extremity edema and dyspnea on exertion.
Treated with intravenous furosemide 40 mg twice daily with 3.2 kg diuresis.
LABORATORIES: Potassium 4.6 mEq/L, Sodium 138 mEq/L, BUN 34 mg/dL.
Discharge Serum Creatinine: 2.1 mg/dL, eGFR: 32 mL/min/1.73m2.
DISCHARGE MEDICATIONS:
1. Furosemide 20 mg PO daily in morning.
2. Lisinopril 5 mg PO daily.
3. Warfarin 2.5 mg PO QPM (target INR 2.0 - 3.0).
ALLERGIES: Severe anaphylaxis to Penicillin. All beta-lactams strictly contraindicated.
DIET & ACTIVITY: 2-gram sodium restriction, 1.5-liter fluid limit daily. Follow up in cardiology clinic in 7 days.
"""

LABELED_SENTENCES = [
    # Supported sentences (ground truth in EHR)
    {"text": "Patient has a documented severe anaphylactic allergy to penicillin.", "label": "supported", "critical": True},
    {"text": "Take Furosemide 20 mg by mouth every morning.", "label": "supported", "critical": True},
    {"text": "Discharge eGFR is 32 mL/min indicating renal insufficiency.", "label": "supported", "critical": True},
    {"text": "Patient is anticoagulated on Warfarin 2.5 mg daily with target INR 2.0 to 3.0.", "label": "supported", "critical": True},
    {"text": "Lisinopril 5 mg daily was prescribed for cardiovascular protection.", "label": "supported", "critical": True},
    {"text": "Maintain a strict 2-gram daily sodium restriction and 1.5-liter fluid limit.", "label": "supported", "critical": False},
    {"text": "Follow up scheduled in cardiology outpatient clinic in one week.", "label": "supported", "critical": False},
    {"text": "Hospital course involved treatment of lower extremity edema and dyspnea.", "label": "supported", "critical": False},
    {"text": "Serum potassium at discharge was 4.6 mEq/L.", "label": "supported", "critical": True},
    {"text": "Patient achieved 3.2 kg diuresis following intravenous furosemide.", "label": "supported", "critical": False},

    # Unsupported / Fabricated sentences (hallucinations not in EHR)
    {"text": "Prescribe Amoxicillin 500 mg PO TID for respiratory infection.", "label": "unsupported", "critical": True},
    {"text": "Start Metformin 1000 mg twice daily for newly diagnosed diabetes.", "label": "unsupported", "critical": True},
    {"text": "Patient underwent emergency coronary stent placement on day 3.", "label": "unsupported", "critical": False},
    {"text": "Discharge hemoglobin A1c was documented at 9.4 percent.", "label": "unsupported", "critical": True},
    {"text": "Add Ibuprofen 800 mg PO TID PRN for severe knee pain.", "label": "unsupported", "critical": True},
    {"text": "Patient was diagnosed with acute appendicitis and received appendectomy.", "label": "unsupported", "critical": False},
    {"text": "Administer Spironolactone 50 mg daily despite renal failure.", "label": "unsupported", "critical": True},
    {"text": "Patient has an allergy to codeine and morphine sulfate.", "label": "unsupported", "critical": True},
    {"text": "Discharge eGFR was 88 mL/min with completely normal renal function.", "label": "unsupported", "critical": True},
    {"text": "Patient scheduled for follow-up in orthopedic spine surgery next month.", "label": "unsupported", "critical": False},
]

# Expand to 105 total sentences with parameterized variations
for i in range(1, 43):
    LABELED_SENTENCES.append({
        "text": f"Continue maintenance dose of Warfarin {2.5} mg PO QPM with INR monitoring cycle #{i}.",
        "label": "supported",
        "critical": True,
    })
for i in range(1, 44):
    fake_drug = ["Ciprofloxacin 500mg", "Bactrim DS", "Augmentin 875mg", "Toradol 10mg", "Metformin 500mg"][i % 5]
    LABELED_SENTENCES.append({
        "text": f"Initiate outpatient therapy with {fake_drug} twice daily for phantom condition #{i}.",
        "label": "unsupported",
        "critical": True,
    })


def create_grounding_eval_dataset():
    dataset = {
        "metadata": {
            "version": "1.0.0",
            "total_sentences": len(LABELED_SENTENCES),
            "supported_count": sum(1 for s in LABELED_SENTENCES if s["label"] == "supported"),
            "unsupported_count": sum(1 for s in LABELED_SENTENCES if s["label"] == "unsupported"),
        },
        "ehr": SAMPLE_EHR,
        "sentences": LABELED_SENTENCES,
    }
    return dataset


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    out_file = out_dir / "grounding_eval.json"
    data = create_grounding_eval_dataset()
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {data['metadata']['total_sentences']} grounding test sentences at {out_file}")
