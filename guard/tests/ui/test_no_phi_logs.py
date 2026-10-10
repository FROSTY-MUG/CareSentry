"""Tests verifying zero PHI / Clinical Record text appears in server logs (U-03, Section 7)."""

import io
import logging
from fastapi.testclient import TestClient

from caresentry_guard.gateway.server import app


def test_zero_record_text_in_server_logs(caplog):
    """Ensure sensitive clinical notes are never printed to logging handlers."""
    client = TestClient(app)
    
    # 1. Create session
    sess_res = client.post("/ui/api/session")
    sess_id = sess_res.json()["session_id"]

    # Unique synthetic patient record text
    secret_phi = "PATIENT_PHI_SECRET_RECORD_ANONYMOUS_491823"
    clinical_note = f"{secret_phi} has documented severe angioedema to penicillin."

    with caplog.at_level(logging.DEBUG):
        # 2. Upload record
        rec_res = client.post("/ui/api/record", json={"session_id": sess_id, "record_text": clinical_note})
        assert rec_res.status_code == 200

        # 3. Check record via /ui/api/check
        check_res = client.post("/ui/api/check", json={"record": clinical_note, "summary": "Amoxicillin prescribed."})
        assert check_res.status_code == 200

    # Ensure secret_phi string NEVER appears in captured logs
    assert secret_phi not in caplog.text, "CRITICAL PRIVACY VIOLATION: Clinical record text was logged!"
