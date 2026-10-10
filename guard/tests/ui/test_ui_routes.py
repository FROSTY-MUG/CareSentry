"""Tests for CareSentry Guard Console UI Routes (U-01, U-04, U-05, U-11)."""

import pytest
from fastapi.testclient import TestClient

from caresentry_guard.gateway.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ui_index_served(client):
    """Test that GET /ui serves the single page HTML shell without network."""
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Guard Console" in resp.text
    assert "Research tool. Not for clinical decision-making" in resp.text


def test_ui_static_assets_served(client):
    """Test that static CSS and JS are correctly mounted and served locally."""
    resp_css = client.get("/ui/static/app.css")
    assert resp_css.status_code == 200
    assert "var(--bg-primary)" in resp_css.text

    resp_js = client.get("/ui/static/app.js")
    assert resp_js.status_code == 200
    assert "CareSentry-AI Guard Console" in resp_js.text

    resp_viz = client.get("/ui/static/attention_visualizer.js")
    assert resp_viz.status_code == 200
    assert "AttentionVisualizer3D" in resp_viz.text


def test_ui_api_status(client):
    """Test GET /ui/api/status returns version, model, installed lanes, and safety notice."""
    resp = client.get("/ui/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert "model_id" in data
    assert "installed_lanes" in data
    assert isinstance(data["installed_lanes"], dict)
    assert "safety_notice" in data
    assert "Research tool" in data["safety_notice"]


def test_session_lifecycle(client):
    """Test creating, attaching record, and deleting in-memory session (U-03, U-11)."""
    # 1. Create session
    resp_sess = client.post("/ui/api/session")
    assert resp_sess.status_code == 200
    sess_data = resp_sess.json()
    session_id = sess_data["session_id"]
    assert session_id.startswith("sess-")

    # 2. Attach record
    sample_ehr = "Patient allergy documented: Severe anaphylaxis to Penicillin. Vitals stable."
    resp_rec = client.post("/ui/api/record", json={"session_id": session_id, "record_text": sample_ehr})
    assert resp_rec.status_code == 200
    rec_data = resp_rec.json()
    assert rec_data["status"] == "attached"
    assert rec_data["word_count"] > 5

    # 3. Delete session
    resp_del = client.request("DELETE", "/ui/api/session", json={"session_id": session_id})
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "cleared"


def test_audit_check_endpoint(client):
    """Test POST /ui/api/check performs model-free invariant checking with line numbers."""
    record = (
        "Line 1: Patient Note\n"
        "Line 2: Known Allergy: Severe Penicillin Anaphylaxis\n"
        "Line 3: Assessment: Bacterial pharyngitis"
    )
    summary_unsafe = "Prescribed amoxicillin 500mg for pharyngitis."

    resp = client.post("/ui/api/check", json={"record": record, "summary": summary_unsafe})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAIL"
    assert len(data["violations"]) > 0
    # Missing constraint should flag penicillin omitted from summary
    assert len(data["missing_constraints"]) > 0
    assert "penicillin" in data["missing_constraints"][0]["constraint"].lower()


def test_export_result_endpoint(client):
    """Test GET /ui/api/export/{result_id} complies with guard_audit_result.v1 schema."""
    resp = client.get("/ui/api/export/demo-123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema"] == "guard_audit_result.v1"
    assert data["result_id"] == "demo-123"
    assert "verdict" in data
    # Ensure raw record text is not in the export
    assert "record_text" not in data
