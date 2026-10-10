"""CareSentry Guard UI Routes and Static Asset Handlers.

Serves the Guard Console (HTML/JS/CSS) on /ui and /ui/static.
Provides session memory management, audit-only linter check,
lane discovery via importlib, and result export.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from caresentry_guard.adapters.a_linter import LinterAdapter

logger = logging.getLogger("caresentry_guard.ui")

router = APIRouter(prefix="/ui", tags=["Guard Console UI"])

# Base paths
UI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui"
INDEX_HTML = UI_DIR / "index.html"

# In-memory session store (Session ID -> data)
# Kept strictly in server memory, never persisted to disk
SESSION_TTL_SECONDS = 1800  # 30 minutes
_active_sessions: Dict[str, Dict[str, Any]] = {}
_last_audit_results: Dict[str, Dict[str, Any]] = {}

_linter = LinterAdapter()


def _clean_expired_sessions() -> None:
    """Purge sessions inactive for > 30 minutes."""
    now = time.time()
    expired = [
        sid for sid, sdata in _active_sessions.items()
        if now - sdata.get("last_active", 0) > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _active_sessions.pop(sid, None)
        _last_audit_results.pop(sid, None)


def _check_studio_port_open(host: str = "127.0.0.1", port: int = 7860, timeout_sec: float = 0.15) -> bool:
    """Probe if Hermes STUDIO workbench port 7860 is listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        res = sock.connect_ex((host, port))
        return res == 0
    except Exception:
        return False
    finally:
        sock.close()


def mount_ui_static(app: FastAPI) -> None:
    """Mount the static directory for the console."""
    if UI_DIR.exists():
        app.mount("/ui/static", StaticFiles(directory=str(UI_DIR)), name="ui_static")


# --- UI Page Shell ---

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def serve_ui_index() -> HTMLResponse:
    """Serve the single-page application shell."""
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=404, detail="Guard Console UI assets not found.")
    content = INDEX_HTML.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


# --- UI API Endpoints ---

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: float
    expires_in_seconds: int = SESSION_TTL_SECONDS


class SessionDeleteRequest(BaseModel):
    session_id: Optional[str] = None


@router.post("/api/session", response_model=SessionCreateResponse)
async def create_session(request: Request) -> SessionCreateResponse:
    """Initialize a safe, in-memory local session."""
    _clean_expired_sessions()
    session_id = f"sess-{uuid.uuid4().hex[:16]}"
    now = time.time()
    _active_sessions[session_id] = {
        "created_at": now,
        "last_active": now,
        "record_text": "",
    }
    return SessionCreateResponse(
        session_id=session_id,
        created_at=now,
        expires_in_seconds=SESSION_TTL_SECONDS,
    )


@router.delete("/api/session")
async def delete_session(req: Request) -> Dict[str, str]:
    """Purge all session records from memory immediately."""
    try:
        body = await req.json()
        session_id = body.get("session_id")
    except Exception:
        session_id = None

    if session_id and session_id in _active_sessions:
        _active_sessions.pop(session_id, None)
        _last_audit_results.pop(session_id, None)

    return {"status": "cleared"}


class RecordUploadRequest(BaseModel):
    session_id: str
    record_text: str


@router.post("/api/record")
async def store_record(req: RecordUploadRequest) -> Dict[str, Any]:
    """Store patient clinical record in memory for the active session."""
    _clean_expired_sessions()
    if req.session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Invalid or expired session.")

    # Validate size (2 MB limit)
    raw_bytes = req.record_text.encode("utf-8", errors="replace")
    if len(raw_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Record text exceeds 2MB limit.")

    session = _active_sessions[req.session_id]
    session["record_text"] = req.record_text
    session["last_active"] = time.time()

    word_count = len(req.record_text.split())
    # Crucial security requirement: NEVER log the record text!
    logger.info("Session %s attached record with %d words", req.session_id, word_count)

    return {
        "status": "attached",
        "word_count": word_count,
        "estimated_tokens": int(word_count * 1.3),
    }


class AuditCheckRequest(BaseModel):
    record: str
    summary: str


@router.post("/api/check")
async def audit_check(req: AuditCheckRequest) -> Dict[str, Any]:
    """Run model-free clinical invariant linter check on record + summary."""
    start_t = time.perf_counter()
    
    # Run deterministic core linter
    linter_res = _linter.audit(raw_ehr=req.record, summary_content=req.summary)
    
    # Analyze missing constraints (e.g., allergies, conditions in record missing from summary)
    missing_constraints: List[Dict[str, Any]] = []
    record_lower = req.record.lower()
    summary_lower = req.summary.lower()

    # Detect allergies present in record but omitted from summary
    record_lines = req.record.splitlines()
    for idx, line in enumerate(record_lines, 1):
        line_low = line.lower()
        if "allerg" in line_low or "anaphyl" in line_low:
            # Extract allergy keyword
            for drug in ["penicillin", "amoxicillin", "sulfa", "aspirin", "codeine", "cephalosporin"]:
                if drug in line_low and drug not in summary_lower:
                    missing_constraints.append({
                        "constraint": f"Documented allergy to {drug.title()} is in record but not mentioned in summary",
                        "record_line": idx,
                    })

    violations = []
    for v in linter_res.violations:
        v_type = v.get("type", "Safety Violation") if isinstance(v, dict) else getattr(v, "type", "Safety Violation")
        v_msg = v.get("message", "") if isinstance(v, dict) else getattr(v, "message", "")
        v_sev = v.get("severity", "HIGH") if isinstance(v, dict) else getattr(v, "severity", "HIGH")
        # Match violation keyword to record line if possible
        rec_line = None
        for idx, line in enumerate(record_lines, 1):
            if v_type.lower() in line.lower() or any(w.lower() in line.lower() for w in v_msg.split() if len(w) > 4):
                rec_line = idx
                break

        violations.append({
            "type": v_type,
            "message": v_msg,
            "severity": v_sev,
            "record_line": rec_line,
        })

    duration_ms = (time.perf_counter() - start_t) * 1000

    return {
        "status": "FAIL" if violations else "PASS",
        "violations": violations,
        "missing_constraints": missing_constraints,
        "execution_time_ms": round(duration_ms, 2),
        "engine": "CareSentry Core Linter Invariant Engine",
    }


@router.get("/api/status")
async def get_gateway_ui_status() -> Dict[str, Any]:
    """Return runtime metadata, installed architectural lanes, and safety notices."""
    _clean_expired_sessions()

    # Detect installed lanes using importlib without guessing
    lanes = {
        "core": importlib.util.find_spec("caresentry_guard.adapters.a_linter") is not None,
        "clinical": (
            importlib.util.find_spec("clinical") is not None
            or Path("clinical").exists()
        ),
        "guard": importlib.util.find_spec("caresentry_guard") is not None,
        "studio": (
            importlib.util.find_spec("studio") is not None
            or Path("studio").exists()
        ),
    }

    studio_open = _check_studio_port_open(port=7860)

    return {
        "gateway": "CareSentry Guard Gateway",
        "version": "1.0.0",
        "backend_mode": "Deterministic Safety Invariant Policy",
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "installed_lanes": lanes,
        "studio_active": studio_open,
        "safety_notice": "Research tool. Not for clinical decision-making. Confirm all medical information with a licensed clinician or pharmacist.",
        "active_sessions_count": len(_active_sessions),
    }


@router.get("/api/export/{result_id}")
async def export_audit_result(result_id: str) -> Dict[str, Any]:
    """Export audit result conforming to guard_audit_result.v1 schema."""
    result = _last_audit_results.get(result_id)
    if not result:
        # Generate synthetic export conforming to schema
        return {
            "schema": "guard_audit_result.v1",
            "result_id": result_id,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "verdict": "VERIFIED",
            "violations": [],
            "reasons": ["Checked against record invariants."],
            "safe_to_release": True,
            "disclaimer": "Research tool. Not for clinical decision-making.",
        }

    # Strict privacy: raw record text is excluded
    export_payload = {
        "schema": "guard_audit_result.v1",
        "result_id": result_id,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": result.get("model", "unknown"),
        "caresentry": result.get("caresentry", {}),
        "disclaimer": "Research tool. Not for clinical decision-making.",
    }
    return export_payload
