"""generate_cases.py

Generates 100 seeded synthetic clinical cases for evaluation.
Each case includes:
- Needle depth (position of the critical constraint in the context)
- Phrasing (how the constraint is expressed)
- Distractors (other medical facts)
- Abbreviations (common clinical abbreviations)
- Needle text (the actual constraint to detect)

Uses a fixed random seed for deterministic output.
"""

import json
import random
import re
from pathlib import Path

# Fixed seed for deterministic output
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Clinical rule templates from clinical_rules.json
RULES = [
    {"class": "ALLERGY", "needle": "Allergy to penicillin", "contraindicated": ["amoxicillin", "augmentin", "ampicillin"]},
    {"class": "ALLERGY", "needle": "Allergy to sulfa", "contraindicated": ["bactrim", "sulfamethoxazole"]},
    {"class": "ALLERGY", "needle": "Allergy to NSAIDs", "contraindicated": ["ibuprofen", "advil", "aspirin"]},
    {"class": "RENAL", "needle": "eGFR < 30 mL/min", "contraindicated": ["metformin", "spironolactone"]},
    {"class": "DDI", "needle": "Warfarin and NSAIDs", "contraindicated": ["warfarin + ibuprofen"]},
]

# Sample patient contexts (templates)
CONTEXT_TEMPLATES = [
    "Patient {age} male, {comorbidities}. Labs: {labs}. Discharge summary: {summary}.",
    "History: {history}. Current meds: {meds}. Discharge instructions: {instructions}.",
    "Clinical notes: {notes}. Past medical history: {pmh}. Medications: {meds}."
]

# Needle positions (percentage through context)
NEEDLE_DEPTHS = [0.1, 0.3, 0.5, 0.7, 0.9]  # Early, early-mid, middle, mid-late, late


def generate_case(i: int) -> dict:
    rule = random.choice(RULES)
    depth = random.choice(NEEDLE_DEPTHS)
    template = random.choice(CONTEXT_TEMPLATES)

    # Generate random context components
    age = random.choice(["68", "74", "82", "65", "71"])
    comorbidities = random.choice(["HTN, DM", "COPD, CKD", "CHF, Asthma", "DM, CKD"])
    labs = random.choice(["BMP: Na 140, K 4.2, Cr 1.8, eGFR 28", "BMP: Na 138, K 4.5, Cr 1.2, eGFR 45", "BMP: Na 142, K 4.3, Cr 2.1, eGFR 22"])
    meds = random.choice(["Lisinopril 10mg daily", "Metformin 500mg BID", "Warfarin 5mg daily", "Ibuprofen 400mg TID"])
    summary = random.choice(["Discharged home with follow-up", "Transferred to rehab", "Discharged to skilled nursing"])
    history = random.choice(["Previous MI in 2020", "Appendectomy 1995", "Chronic back pain", "No significant history"])
    instructions = random.choice(["Take meds as directed", "Follow up in 2 weeks", "Monitor blood pressure"])
    notes = random.choice(["Patient alert and oriented", "Needs assistance with ADLs", "Vitals stable"])

    # Build full context
    context = template.format(
        age=age, comorbidities=comorbidities, labs=labs,
        meds=meds, summary=summary, history=history,
        instructions=instructions, notes=notes
    )

    # Insert needle at specified depth
    words = context.split()
    needle_words = rule["needle"].split()
    needle_len = len(needle_words)
    insert_pos = int(depth * len(words))
    if insert_pos + needle_len > len(words):
        insert_pos = max(0, len(words) - needle_len)

    # Insert needle and mark position
    needle_start = insert_pos
    needle_end = insert_pos + needle_len
    words[needle_start:needle_end] = needle_words
    final_context = " ".join(words)

    # Create distractors (other rules not the target)
    distractors = []
    for other_rule in RULES:
        if other_rule != rule:
            distractor = other_rule["needle"]
            # Add as a distractor sentence at end
            distractors.append(distractor)
    distractor_text = " " + "; ".join(distractors[:2])

    # Generate abbreviations
    abbreviations = ["BP", "HR", "T", "RR", "O2", "BMP", "eGFR", "DM", "HTN", "CHF"]
    abbrev_text = " " + " ".join(random.sample(abbreviations, min(3, len(abbreviations))))

    # Full document
    full_doc = final_context + distractor_text + abbrev_text

    # Generate summary that may or may not include contraindicated drug
    contraindicated = rule["contraindicated"]
    include_violation = random.choice([True, False])
    if include_violation:
        violation_med = random.choice(contraindicated)
        summary_with_violation = f"Discharge on {violation_med} {random.choice(['daily', 'BID', 'TID'])}."
    else:
        safe_med = random.choice(["Lisinopril", "Amlodipine", "Metoprolol"])
        summary_with_violation = f"Discharge on {safe_med} {random.choice(['daily', 'BID'])}."

    return {
        "id": f"case_{i:03d}",
        "context": full_doc,
        "needle": rule["needle"],
        "needle_depth": depth,
        "needle_class": rule["class"],
        "summary": summary_with_violation,
        "include_violation": include_violation,
        "contraindicated_drugs": rule["contraindicated"],
        "distractors": distractors,
        "abbreviations": abbreviations,
        "seed": RANDOM_SEED,
    }


def main():
    cases = [generate_case(i) for i in range(100)]
    output_path = Path("eval") / "data" / "synthetic_cases_100.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} synthetic cases in {output_path}")
    print(f"Seed: {RANDOM_SEED} (deterministic)")


if __name__ == "__main__":
    main()
