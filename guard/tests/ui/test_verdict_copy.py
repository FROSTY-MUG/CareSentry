"""Tests for Guard Console Verdict Copy and Approved Language (U-02, U-06)."""

import json
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui"
EN_JSON = UI_DIR / "i18n" / "en.json"
INDEX_HTML = UI_DIR / "index.html"
APP_JS = UI_DIR / "app.js"


def test_copy_catalog_exists_and_valid():
    """Ensure en.json is loaded and contains all four verdict end states."""
    assert EN_JSON.exists(), "ui/i18n/en.json must exist"
    copy = json.loads(EN_JSON.read_text(encoding="utf-8"))

    verdicts = copy["verdict"]
    expected_states = ["verified", "annotated", "withheld", "abstain"]
    for state in expected_states:
        assert f"{state}_title" in verdicts, f"Missing {state}_title in copy catalog"
        assert f"{state}_summary" in verdicts, f"Missing {state}_summary in copy catalog"
        assert f"{state}_action" in verdicts, f"Missing {state}_action in copy catalog"


def test_withheld_verdict_conceals_unverified_text_by_default():
    """Ensure that app.js conceals WITHHELD output behind a labeled reveal control."""
    app_js_text = APP_JS.read_text(encoding="utf-8")
    
    # Assert that reveal control has secondary styling and specific warning
    assert "Show unverified text (not safe to follow)" in app_js_text
    assert "withheld-concealed-notice" in app_js_text
    assert "unverified-revealed-text" in app_js_text
    assert "display:none" in app_js_text, "Unverified text pane must be hidden by default"


def test_plain_language_verdict_words():
    """Verify that copy uses plain words (not technical jargon like 'omission' or 'abstention')."""
    copy = json.loads(EN_JSON.read_text(encoding="utf-8"))
    verdicts = copy["verdict"]

    # Verify plain language approved copy
    assert "Checked against the record. No issues found." in verdicts["verified_summary"]
    assert "COULD NOT VERIFY" in verdicts["abstain_title"]
    assert "Do not follow this advice. Please consult your care team." in verdicts["withheld_action"]

    # Jargon must not appear in user-facing verdict summary
    assert "abstention" not in verdicts["abstain_summary"].lower()
    assert "heuristic" not in verdicts["verified_summary"].lower()


def test_safety_notice_present_in_all_surfaces():
    """Verify that the official safety notice is consistent across copy and HTML."""
    copy = json.loads(EN_JSON.read_text(encoding="utf-8"))
    notice = copy["app"]["safety_notice"]
    assert "Research tool. Not for clinical decision-making" in notice

    html_text = INDEX_HTML.read_text(encoding="utf-8")
    assert notice in html_text
