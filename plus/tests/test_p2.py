"""Unit tests for P2 features: F-15 PDF Ingestion & F-16 Multilingual Readability."""

import pytest
from caresentry_plus.ingest.pdf_reader import PDFRecordIngestion, UnreadableScannedDocumentError
from caresentry_plus.lang.multilingual import MultilingualLanguageSentry


def test_pdf_ingestion_clear_error_on_empty(tmp_path):
    """F-15: PDF ingestion fails clearly on unreadable or empty documents."""
    empty_pdf = tmp_path / "blank_scan.pdf"
    empty_pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    ingest = PDFRecordIngestion()
    with pytest.raises(Exception) as excinfo:
        ingest.extract_text(empty_pdf)
    assert issubclass(excinfo.type, Exception)


def test_multilingual_mentions_detection():
    """F-16: Hindi and Spanish clinical term detection."""
    lang_sentry = MultilingualLanguageSentry()

    # Hindi mention
    hindi_text = "रोगी को पेनिसिलिन एलर्जी है और गुर्दे की बीमारी है।"
    hi_matches = lang_sentry.detect_multilingual_mentions(hindi_text)
    assert len(hi_matches) >= 1
    assert any(m["canonical_concept"] == "penicillin" for m in hi_matches)

    # Spanish mention
    spanish_text = "El paciente tiene alergia a la penicilina y daño renal."
    es_matches = lang_sentry.detect_multilingual_mentions(spanish_text)
    assert len(es_matches) >= 1
    assert any(m["canonical_concept"] == "penicillin" for m in es_matches)


def test_readability_metrics_scoring():
    """F-16: Patient discharge summary readability score."""
    lang_sentry = MultilingualLanguageSentry()

    # Simple patient-accessible text
    simple_summary = (
        "Take one pill by mouth each day with breakfast. "
        "Do not stop taking this medicine unless your doctor tells you. "
        "Drink plenty of water every day. Call our clinic if you feel dizzy."
    )
    metrics_simple = lang_sentry.calculate_readability(simple_summary)
    assert metrics_simple.flesch_reading_ease >= 60.0
    assert metrics_simple.flesch_kincaid_grade_level <= 8.0
    assert "PATIENT_ACCESSIBLE" in metrics_simple.reading_accessibility

    # Complex clinical jargon
    complex_summary = (
        "Following transcatheter pharmacological intervention, hypercholesterolemia and asymptomatic "
        "glomerulonephritis necessitate pharmacokinetic titration of hydroxymethylglutaryl-CoA reductase inhibitors."
    )
    metrics_complex = lang_sentry.calculate_readability(complex_summary)
    assert metrics_complex.flesch_kincaid_grade_level > 10.0
