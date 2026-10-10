"""CareSentry Guard OpenAI-Compatible Safety Gateway Server.

Exposes /v1/chat/completions and /v1/models on 127.0.0.1:8787.
Injects pre-flight injection scanning, post-flight invariant verification,
evidence grounding, and deterministic withholding policies.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from caresentry_guard.adapters.a_linter import LinterAdapter
from caresentry_guard.adapters.a_probe import ProbeAdapter
from caresentry_guard.adapters.a_runner import RunnerAdapter
from caresentry_guard.deid.scrubber import DeidentificationScrubber
from caresentry_guard.grounding.engine import EvidenceGroundingEngine
from caresentry_guard.injection.scanner import ClinicalInjectionScanner, InjectionAction
from caresentry_guard.policy.engine import PolicyDecision, PolicyState, SafetyPolicyEngine

logger = logging.getLogger("caresentry_guard.gateway")

app = FastAPI(
    title="CareSentry Guard OpenAI-Compatible Safety Gateway",
    version="1.0.0",
    description="Deterministic Clinical Invariant & Attention Sentry Gateway for Open-Weight Models",
)

# Global sub-engines
_linter = LinterAdapter()
_scanner = ClinicalInjectionScanner(action=InjectionAction.NEUTRALIZE)
_grounder = EvidenceGroundingEngine()
_policy = SafetyPolicyEngine()
_scrubber = DeidentificationScrubber()
_runner = RunnerAdapter(force_simulation=True)
_probe = ProbeAdapter(runner_adapter=_runner)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False
    clinical_record: Optional[str] = None  # Optional explicit EHR context parameter


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = 1728550000
    owned_by: str = "caresentry-guard"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]


@app.get("/v1/models")
async def list_models() -> ModelListResponse:
    """Return available open-weight models guarded by CareSentry."""
    models = [
        ModelCard(id="Qwen/Qwen2.5-1.5B-Instruct"),
        ModelCard(id="Qwen/Qwen2.5-7B-Instruct"),
        ModelCard(id="google/gemma-2-9b-it"),
    ]
    return ModelListResponse(data=models)


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, response: Response) -> Dict[str, Any]:
    """Execute guarded chat completion pipeline."""
    # 1. Reconstruct prompt and extract clinical EHR
    full_prompt = "\n".join([m.content for m in req.messages])
    ehr_text = req.clinical_record or full_prompt

    # 2. Pre-flight: Prompt Injection Scanner
    scan_res = _scanner.scan(full_prompt)

    # 3. Model Generation (with simulated fallback for instant offline execution)
    # If injection detected, immediately invoke policy engine
    if scan_res.has_injection:
        decision = _policy.evaluate(
            raw_summary="",
            linter_status="FAIL",
            linter_violations=[],
            injection_detected=True,
            injection_findings=scan_res.findings,
            grounding_score=0.0,
            safety_critical_violations=1,
        )
    else:
        # Check if the prompt has documented penicillin allergy or renal impairment
        # to produce realistic model draft output
        allergies = _linter.extract_allergies(ehr_text)
        renal = _linter.extract_renal(ehr_text)

        # Baseline draft summary (simulating open-weight model's lost-in-the-middle tendency)
        if any("penicillin" in a["allergy_class"] for a in allergies):
            # Model generated tempting unsafe order
            draft_summary = (
                "Geriatric discharge plan: Patient is recovering well from pneumonia. "
                "Prescribe Amoxicillin 500 mg PO TID for 7 days to complete antibiotic coverage. "
                "Continue ambulation exercises."
            )
        elif renal.get("egfr") and renal["egfr"] < 30:
            draft_summary = (
                "Geriatric discharge instructions: Patient managed for renal dehydration. "
                "Resume Metformin 1000 mg PO BID to optimize blood glucose control. Follow up in 10 days."
            )
        else:
            draft_summary = (
                "Geriatric discharge instructions: Patient cleared for discharge. "
                "Take Acetaminophen 500 mg PO PRN for discomfort. Follow up in 7 days."
            )

        # 4. Post-flight: Deterministic Invariant Audit & Evidence Grounding
        audit_rep = _linter.audit(ehr_text, draft_summary)
        grounding_rep = _grounder.audit_grounding(ehr_text, draft_summary)

        # 5. Policy Decision
        decision = _policy.evaluate(
            raw_summary=draft_summary,
            linter_status=audit_rep.status,
            linter_violations=audit_rep.violations,
            injection_detected=False,
            injection_findings=[],
            grounding_score=grounding_rep.overall_grounding_score,
            safety_critical_violations=grounding_rep.safety_critical_violations,
        )

    # 6. Construct OpenAI-compatible response with CareSentry headers and telemetry
    response.headers["X-CareSentry-Status"] = decision.state.value
    response.headers["X-CareSentry-Violations"] = str(len(decision.audit_metadata.get("violations", [])))

    created_ts = int(time.time())
    resp_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    return {
        "id": resp_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": decision.summary_to_emit,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(full_prompt.split()),
            "completion_tokens": len(decision.summary_to_emit.split()),
            "total_tokens": len(full_prompt.split()) + len(decision.summary_to_emit.split()),
        },
        "caresentry": {
            "guard_version": "1.0.0",
            "policy_state": decision.state.value,
            "is_safe_to_release": decision.is_safe_to_release,
            "reasons": decision.reasons,
            "escalate_to_human": decision.escalate_to_human,
            "injection_findings": [f.explanation for f in scan_res.findings],
            "audit_metadata": decision.audit_metadata,
        },
    }


# Mount Guard Console UI (Track C Web Console)
try:
    from caresentry_guard.gateway.ui_routes import mount_ui_static, router as ui_router
    mount_ui_static(app)
    app.include_router(ui_router)
except Exception as _ui_err:
    logger.warning("Could not mount Guard Console UI: %s", _ui_err)

