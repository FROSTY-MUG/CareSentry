"""Labeled clinical assertion dataset for ContextFilter validation.

Contains 65 clinically realistic assertions annotated with ground-truth
modality, target entity, and expected active-risk status.
"""

LABELED_ASSERTION_DATASET = [
    # --- AFFIRMED (ACTIVE RISK) ---
    {"text": "Patient has severe allergy to penicillin, causing hives and dyspnea.", "entity": "penicillin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Documented anaphylactic reaction to amoxicillin in 2021.", "entity": "amoxicillin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Allergies: Bactrim (angioedema and throat swelling).", "entity": "bactrim", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Patient is allergic to sulfa medications with diffuse rash.", "entity": "sulfa", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Known severe adverse reaction to ibuprofen resulting in bronchospasm.", "entity": "ibuprofen", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Documented aspirin-exacerbated respiratory disease (AERD).", "entity": "aspirin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Active order for warfarin 5 mg daily for atrial fibrillation.", "entity": "warfarin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Current medications include spironolactone 25 mg PO daily.", "entity": "spironolactone", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Discharge medication list contains metformin 1000 mg BID.", "entity": "metformin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Allergy confirmed: Cipro resulted in Achilles tendonitis.", "entity": "cipro", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "True allergy to cephalexin with facial swelling and hives.", "entity": "cephalexin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "EHR records demonstrate confirmed allergy to toradol.", "entity": "toradol", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Patient reports severe allergy to codeine with respiratory distress.", "entity": "codeine", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Allergy list: Augmentin (severe gastrointestinal reaction and rash).", "entity": "augmentin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Hypersensitivity to naproxen documented by outpatient allergist.", "entity": "naproxen", "expected_status": "AFFIRMED", "expected_active": True},

    # --- NEGATED (SUPPRESSED) ---
    {"text": "Patient has no known drug allergies (NKDA).", "entity": "penicillin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "No known penicillin allergy reported by patient or proxy.", "entity": "penicillin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Patient denies any allergy to amoxicillin or other penicillins.", "entity": "amoxicillin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Penicillin allergy was ruled out following skin testing in clinic.", "entity": "penicillin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Sulfa allergy excluded after formal inpatient allergy consult.", "entity": "sulfa", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Patient without known allergy to aspirin or NSAIDs.", "entity": "aspirin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Denies sulfa allergy, states previous chart was inaccurate.", "entity": "sulfa", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Patient has no documented history of allergic reactions to ibuprofen.", "entity": "ibuprofen", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Negative for drug allergies upon admission interview.", "entity": "metformin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Patient does not have a known allergy to Bactrim.", "entity": "bactrim", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Free of allergic reaction to cephalosporins.", "entity": "cephalosporin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Allergy to Augmentin was negated after negative challenge.", "entity": "augmentin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Patient denies allergy to morphine or other narcotics.", "entity": "morphine", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Chart review confirms patient is not allergic to heparin.", "entity": "heparin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "No adverse reaction to toradol documented in past surgical notes.", "entity": "toradol", "expected_status": "NEGATED", "expected_active": False},

    # --- HISTORICAL TOLERANCE (SUPPRESSED) ---
    {"text": "Patient tolerated amoxicillin in 2019 without any adverse reaction.", "entity": "amoxicillin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Completed 10-day Augmentin course last year without incident.", "entity": "augmentin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Took penicillin in 2018 for strep pharyngitis with no problem.", "entity": "penicillin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Childhood reaction to ampicillin resolved after formal oral re-challenge.", "entity": "ampicillin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Patient tolerated Bactrim well during prior UTI treatment.", "entity": "bactrim", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Previously received ceftriaxone without allergic complications.", "entity": "ceftriaxone", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Discontinued lisinopril 3 years ago due to dry cough, not allergy.", "entity": "lisinopril", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Formerly on metformin in 2020, stopped when diet controlled.", "entity": "metformin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Patient took naproxen previously without complication.", "entity": "naproxen", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "No reaction upon receiving cefazolin perioperatively last month.", "entity": "cefazolin", "expected_status": "HISTORICAL", "expected_active": False},

    # --- FAMILY HISTORY (SUPPRESSED FOR PATIENT) ---
    {"text": "Patient's mother has severe penicillin allergy with anaphylaxis.", "entity": "penicillin", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Father had severe sulfa allergy; patient has never taken it.", "entity": "sulfa", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Family history of adverse reaction to anesthesia (malignant hyperthermia).", "entity": "anesthesia", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Sister has documented anaphylaxis to aspirin and NSAIDs.", "entity": "aspirin", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "FHx: maternal allergy to codeine with urticaria.", "entity": "codeine", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Brother developed rash on amoxicillin, patient denies personal reaction.", "entity": "amoxicillin", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Family history notable for penicillin allergy in father.", "entity": "penicillin", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Maternal history of allergy to Bactrim.", "entity": "bactrim", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Patient mentions daughter is allergic to cephalexin.", "entity": "cephalexin", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Parent has severe allergy to ciprofloxacin.", "entity": "ciprofloxacin", "expected_status": "FAMILY_HISTORY", "expected_active": False},

    # --- AMBIGUOUS (FAIL SAFE -> ACTIVE RISK PRESERVED) ---
    {"text": "Patient reports possible mild reaction to penicillin decades ago.", "entity": "penicillin", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Questionable allergy to sulfa; patient cannot recall specifics.", "entity": "sulfa", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Uncertain whether childhood rash was caused by amoxicillin or viral exanthem.", "entity": "amoxicillin", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Suspected adverse reaction to erythromycin reported by family.", "entity": "erythromycin", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Patient thinks they might be allergic to aspirin, unconfirmed.", "entity": "aspirin", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Equivocal chart note regarding tolerance of cephalosporins.", "entity": "cephalosporin", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Possible allergy to codeine according to nursing notes.", "entity": "codeine", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Unclear history of reaction following Bactrim ingestion.", "entity": "bactrim", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Probable hypersensitivity to ibuprofen noted during clinic visit.", "entity": "ibuprofen", "expected_status": "AMBIGUOUS", "expected_active": True},
    {"text": "Patient cannot recall if reaction was to amoxicillin or augmentin.", "entity": "amoxicillin", "expected_status": "AMBIGUOUS", "expected_active": True},

    # --- ADDITIONAL CLINICAL EDGE CASES ---
    {"text": "Patient denies allergy to penicillin, but experienced nausea once.", "entity": "penicillin", "expected_status": "NEGATED", "expected_active": False},
    {"text": "Allergy to penicillin confirmed on chart, avoid all beta-lactams.", "entity": "penicillin", "expected_status": "AFFIRMED", "expected_active": True},
    {"text": "Mother had angioedema with ACE inhibitors; patient currently denies allergy.", "entity": "ace inhibitor", "expected_status": "FAMILY_HISTORY", "expected_active": False},
    {"text": "Tolerated ciprofloxacin in 2022 during acute diverticulitis episode.", "entity": "ciprofloxacin", "expected_status": "HISTORICAL", "expected_active": False},
    {"text": "Questionable allergy to vancomycin after red man syndrome event.", "entity": "vancomycin", "expected_status": "AMBIGUOUS", "expected_active": True},
]
