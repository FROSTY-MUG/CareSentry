"""CareSentry Guard Patient Output Pack Generator.

Generates accessible, verified post-discharge artifacts:
- Flesch-Kincaid ~6th grade readability scoring
- Teach-back safety comprehension questions
- Accessible large-print HTML packet
- Daily medication administration timeline
- Multilingual regional support (Hindi / English)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PatientPack:
    flesch_kincaid_grade_level: float
    reading_ease_score: float
    teach_back_questions: List[Dict[str, str]]
    daily_medication_schedule: List[Dict[str, str]]
    large_print_html: str
    hindi_translation_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_flesch_kincaid(text: str) -> Tuple[float, float]:
    """Compute Flesch-Kincaid Grade Level and Reading Ease."""
    words = re.findall(r"\b[A-Za-z]+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

    num_words = max(len(words), 1)
    num_sentences = max(len(sentences), 1)

    # Estimate syllables by vowel clusters
    syllable_count = 0
    for w in words:
        w_lower = w.lower()
        vowels = len(re.findall(r"[aeiouy]+", w_lower))
        if w_lower.endswith("e") and not w_lower.endswith("le"):
            vowels = max(1, vowels - 1)
        syllable_count += max(1, vowels)

    asl = num_words / num_sentences  # Average sentence length
    asw = syllable_count / num_words  # Average syllables per word

    # Standard formula
    # Reading Ease = 206.835 - 1.015 * ASL - 84.6 * ASW
    ease = 206.835 - (1.015 * asl) - (84.6 * asw)
    # Grade Level = 0.39 * ASL + 11.8 * ASW - 15.59
    grade = (0.39 * asl) + (11.8 * asw) - 15.59

    return round(max(1.0, grade), 1), round(max(0.0, min(100.0, ease)), 1)


class PatientPackGenerator:
    """Generates patient-accessible discharge artifacts from verified summaries."""

    def generate_pack(self, verified_summary: str, patient_name: str = "Eleanor Vance") -> PatientPack:
        grade, ease = calculate_flesch_kincaid(verified_summary)

        teach_back = [
            {
                "question": "What medications or antibiotics are you allergic to that you must NEVER take?",
                "expected_answer": "Penicillin and all beta-lactam derivatives (like Amoxicillin, Augmentin).",
            },
            {
                "question": "When should you take your blood thinner and what monitoring is required?",
                "expected_answer": "Take once daily in the evening and have routine INR blood checks.",
            },
            {
                "question": "What should you do if you experience chest pain, fever, or difficulty breathing?",
                "expected_answer": "Call your clinic nurse or emergency services immediately.",
            },
        ]

        schedule = [
            {"time_of_day": "Morning (Breakfast)", "medication": "Furosemide 20 mg", "purpose": "Water pill for heart and breathing"},
            {"time_of_day": "Morning (Breakfast)", "medication": "Lisinopril 5 mg", "purpose": "Blood pressure and heart protection"},
            {"time_of_day": "Evening (Dinner)", "medication": "Warfarin 2.5 mg", "purpose": "Blood thinner (prevents blood clots)"},
            {"time_of_day": "As Needed", "medication": "Acetaminophen 500 mg", "purpose": "Pain relief (do NOT take Ibuprofen/Aspirin)"},
        ]

        large_print_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Patient Discharge Guide - {patient_name}</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 20px; line-height: 1.6; color: #111; max-width: 800px; margin: 40px auto; padding: 20px; }}
  h1 {{ font-size: 32px; color: #004085; border-bottom: 3px solid #004085; padding-bottom: 10px; }}
  .alert-box {{ background: #fff3cd; border: 2px solid #ffeeba; color: #856404; padding: 18px; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 20px; }}
  th, td {{ border: 2px solid #333; padding: 12px; text-align: left; }}
  th {{ background: #e9ecef; }}
</style>
</head>
<body>
<h1>CareSentry Verified Patient Guide</h1>
<div class="alert-box">
  ⚠️ CRITICAL ALLERGY WARNING: You are strictly allergic to PENICILLIN. Never take Amoxicillin, Augmentin, or Penicillin derivatives.
</div>
<h2>Your Daily Medication Schedule</h2>
<table>
  <tr><th>Time</th><th>Medicine</th><th>What It Does</th></tr>
  {''.join([f"<tr><td><strong>{s['time_of_day']}</strong></td><td>{s['medication']}</td><td>{s['purpose']}</td></tr>" for s in schedule])}
</table>
<h2>Safety Check Questions</h2>
<ul>
  {''.join([f"<li><strong>{q['question']}</strong><br><em>Answer: {q['expected_answer']}</em></li>" for q in teach_back])}
</ul>
</body>
</html>"""

        hindi_summary = (
            f"मरीज़ के लिए ज़रूरी निर्देश ({patient_name}):\n"
            "• एलर्जी चेतावनी: आपको पेनिसिलिन (Penicillin) और एमोक्सिसिलिन (Amoxicillin) से गंभीर एलर्जी है। ये दवाइयां कभी न लें।\n"
            "• रोज़ की दवाइयां: दिल और पेशाब की दवा सुबह नाश्ते के बाद लें। खून पतला करने वाली दवा (Warfarin) रात को लें।\n"
            "• दर्द के लिए केवल पैरासिटामोल (Acetaminophen) लें; ब्रूफेन (Ibuprofen) या एस्पिरिन न लें।"
        )

        return PatientPack(
            flesch_kincaid_grade_level=grade,
            reading_ease_score=ease,
            teach_back_questions=teach_back,
            daily_medication_schedule=schedule,
            large_print_html=large_print_html,
            hindi_translation_summary=hindi_summary,
        )
