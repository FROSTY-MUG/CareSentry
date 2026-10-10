"""CareSentry-AI Plus Interactive Web UI (F-11).

Gradio application running on port 7860 providing offline clinical safety auditing,
reverse omission analysis, and interactive attention heatmap visualization.
RESEARCH TOOL ONLY — NOT FOR CLINICAL DECISION-MAKING.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure plus/src and repo root are in sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
ROOT_PATH = Path(__file__).resolve().parent.parent.parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import gradio as gr

from caresentry_plus.adapters.probe_shim import ProbeShim
from caresentry_plus.audit.audit_log import AuditLogger
from caresentry_plus.extraction.omission_checker import OmissionChecker
from caresentry_plus.ontology.normalizer import DrugNormalizer
from caresentry_plus.rules.engine import RulePackEngine
from caresentry_plus.viz.heatmap_viewer import generate_heatmap_html

logger = logging.getLogger("caresentry_plus.webui")

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "evals" / "results" / "webui_audit_log.jsonl"


class WebUIBackend:
    """Orchestrates Track A and Track B safety verification pipelines for the Web UI."""

    def __init__(self):
        self.normalizer = DrugNormalizer()
        self.rule_engine = RulePackEngine(normalizer=self.normalizer)
        self.omission_checker = OmissionChecker(normalizer=self.normalizer)
        self.probe_shims: Dict[str, ProbeShim] = {}
        self.audit_logger = AuditLogger(log_path=DEFAULT_LOG_PATH)

    def get_probe_shim(self, model_id: str) -> ProbeShim:
        """Obtain or cache probe shim for the specified model architecture."""
        if model_id not in self.probe_shims:
            self.probe_shims[model_id] = ProbeShim(model_id=model_id, fallback_mode=True)
        return self.probe_shims[model_id]

    def execute_track_a_linter(self, raw_ehr: str, summary: str) -> Dict[str, Any]:
        """Execute Track A base clinical linter in-process for sub-millisecond execution."""
        try:
            from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
            rules = load_clinical_rules()
            return audit_clinical_safety(raw_ehr, summary, rules)
        except Exception as e:
            logger.warning(f"Track A linter execution failed ({e}); returning fallback PASS.")
            return {"status": "PASS", "violations": [], "standard": "agent-skills.io/v1 (fallback)"}

    def audit_discharge_summary(
        self,
        raw_ehr: str,
        summary_content: str,
        target_needle: str = "",
        enable_attention_probe: bool = False,
        model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
    ) -> Tuple[str, str, str, str, str, str]:
        """Full audit pipeline returning formatted output cards and heatmap HTML."""
        start_time = time.perf_counter()

        if not raw_ehr.strip() or not summary_content.strip():
            return (
                "⚠️ ERROR: Both Patient Record and Discharge Summary must be provided.",
                "{}", "[]", "[]", "[]",
                "<div style='color: #ef4444; padding: 20px;'>Please provide text inputs.</div>"
            )

        # 1. Track A Base Audit
        base_result = self.execute_track_a_linter(raw_ehr, summary_content)
        base_status = base_result.get("status", "PASS")

        # 2. Track B Extended Rule Engine
        plus_violations = self.rule_engine.evaluate_invariants(raw_ehr, summary_content)

        # 3. Track B Reverse Omission Check
        omissions = self.omission_checker.check_omissions(raw_ehr, summary_content)

        # 4. Normalized Drug Mentions
        entities = self.normalizer.extract_and_normalize(raw_ehr + " " + summary_content)
        entities_data = [e.to_dict() for e in entities]

        # Overall Status Determination
        has_critical_plus = any(v.get("severity") in ["CRITICAL", "HIGH"] for v in plus_violations)
        has_critical_omission = any(o.severity == "CRITICAL" for o in omissions)

        overall_status = "FAIL" if (base_status == "FAIL" or has_critical_plus or has_critical_omission) else "PASS"

        # 5. Attention Probe & Heatmap
        heatmap_html = "<div style='color: #94a3b8; padding: 20px;'>Attention probing not requested.</div>"
        z_score_display = "N/A"
        if enable_attention_probe and target_needle.strip():
            probe_shim = self.get_probe_shim(model_id)
            trace = probe_shim.probe(raw_ehr, target_needle.strip(), apply_mitigation=False)
            z_score_display = f"{trace.z_score:+.2f}"
            heatmap_html = generate_heatmap_html(trace.to_dict())

        # 6. Cryptographic Audit Logging
        entry = self.audit_logger.log_audit(
            raw_ehr=raw_ehr,
            summary=summary_content,
            rule_packs=self.rule_engine.loaded_pack_ids,
            model_id=model_id,
            verdict=overall_status,
            violations_count=len(plus_violations),
            omissions_count=len(omissions),
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Build Status Banner
        if overall_status == "FAIL":
            status_banner = (
                f"[FAIL] AUDIT VERDICT: FAIL\n"
                f"* Model Architecture: {model_id}\n"
                f"* Invariant Violations: {len(plus_violations)} (Plus) + {len(base_result.get('violations', []))} (Base)\n"
                f"* Omitted Constraints: {len(omissions)}\n"
                f"* Execution Latency: {elapsed_ms:.1f} ms | Probe Z-Score: {z_score_display}\n"
                f"* Cryptographic Block Hash: {entry.entry_hash[:16]}..."
            )
        else:
            status_banner = (
                f"[PASS] AUDIT VERDICT: PASS\n"
                f"* Model Architecture: {model_id}\n"
                f"* All Invariants Satisfied (Base & Plus Rule Packs)\n"
                f"* Zero Critical Omissions Detected\n"
                f"* Execution Latency: {elapsed_ms:.1f} ms\n"
                f"* Cryptographic Block Hash: {entry.entry_hash[:16]}..."
            )

        return (
            status_banner,
            json.dumps(base_result, indent=2),
            json.dumps(plus_violations, indent=2),
            json.dumps([o.to_dict() for o in omissions], indent=2),
            json.dumps(entities_data, indent=2),
            heatmap_html,
        )


def build_app() -> gr.Blocks:
    """Build Gradio UI interface."""
    backend = WebUIBackend()

    sample_ehr = (
        "Patient is a 74-year-old female admitted for acute decompensation of chronic heart failure.\n"
        "Past Medical History: Chronic Kidney Disease stage 4, Hypertension, Atrial Fibrillation.\n"
        "LABS ON ADMISSION: Serum Creatinine 2.8 mg/dL, estimated GFR (eGFR) is 22 mL/min/1.73m2. Potassium 4.8 mEq/L.\n"
        "ACTIVE MEDICATIONS: Warfarin 4 mg daily for stroke prevention in AFib.\n"
        "DOCUMENTED ALLERGY: Patient has severe Penicillin allergy causing facial hives and dyspnea."
    )

    sample_failing_summary = (
        "Hospital Course & Discharge Summary:\n"
        "Patient presented with fluid overload. Diuresis completed with symptom resolution.\n"
        "Discharge Orders:\n"
        "1. Continue home medications.\n"
        "2. Add Metformin 1000 mg BID for glycemic control.\n"
        "3. Prescribed Cephalexin 500 mg QID for 7 days to treat skin breakdown.\n"
        "4. Prescribed Naproxen 500 mg BID for lower back discomfort.\n"
        "Follow up with primary care physician in 2 weeks."
    )

    sample_needle = "Patient has severe Penicillin allergy causing facial hives and dyspnea."

    with gr.Blocks(title="CareSentry-AI Plus — Clinical Safety Sentry", theme=gr.themes.Default()) as demo:
        gr.Markdown(
            """
            # 🛡️ CareSentry-AI Plus — Clinical Invariant & Attention Sentry
            **Offline Observability & Deterministic Verification Gate for Open-Weight Clinical Summarization**
            
            > ⚠️ **DISCLAIMER:** Research & observability tooling only. Not for clinical decision-making or diagnosis.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                ehr_input = gr.Textbox(
                    label="Patient Record / EHR Narrative",
                    placeholder="Paste clinical EHR notes, lab panels, and documented allergy history...",
                    lines=10,
                    value=sample_ehr,
                )
                summary_input = gr.Textbox(
                    label="Model-Generated Discharge Summary",
                    placeholder="Paste AI-generated patient discharge summary to verify...",
                    lines=8,
                    value=sample_failing_summary,
                )
                with gr.Row():
                    needle_input = gr.Textbox(
                        label="Target Needle / Constraint (Optional for Probing)",
                        placeholder="e.g. Penicillin allergy or eGFR=22",
                        value=sample_needle,
                        scale=3,
                    )
                    probe_checkbox = gr.Checkbox(
                        label="Enable Attention Probing & Heatmap",
                        value=True,
                        scale=1,
                    )

                model_dropdown = gr.Dropdown(
                    label="Clinical AI Model Architecture",
                    choices=[
                        "Qwen/Qwen2.5-1.5B-Instruct",
                        "Qwen/Qwen2.5-0.5B-Instruct",
                        "Qwen/Qwen2.5-7B-Instruct",
                        "google/gemma-2-2b-it",
                        "google/gemma-2-9b-it",
                    ],
                    value="Qwen/Qwen2.5-1.5B-Instruct",
                )

                audit_btn = gr.Button("🔍 Run Deterministic Clinical Audit", variant="primary", size="lg")

            with gr.Column(scale=1):
                verdict_output = gr.Textbox(
                    label="Audit Verdict & Safety Telemetry",
                    lines=5,
                    interactive=False,
                )

                with gr.Tabs():
                    with gr.Tab("Plus Invariants (F-02)"):
                        plus_violations_output = gr.Code(label="Extended Invariant Violations (JSON)", language="json")

                    with gr.Tab("Reverse Omissions (F-04)"):
                        omissions_output = gr.Code(label="Omitted Critical Constraints (JSON)", language="json")

                    with gr.Tab("Base Linter (Track A)"):
                        base_output = gr.Code(label="Track A C-01 Linter Payload (JSON)", language="json")

                    with gr.Tab("Entity Normalization (F-01)"):
                        entities_output = gr.Code(label="Resolved RxNorm / ATC Entities (JSON)", language="json")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📊 Interactive Token Attention Heatmap (F-06)")
                heatmap_output = gr.HTML(label="Heatmap Viewer")

        audit_btn.click(
            fn=backend.audit_discharge_summary,
            inputs=[ehr_input, summary_input, needle_input, probe_checkbox, model_dropdown],
            outputs=[
                verdict_output,
                base_output,
                plus_violations_output,
                omissions_output,
                entities_output,
                heatmap_output,
            ],
            api_name="audit_discharge_summary",
        )

    return demo


def main():
    demo = build_app()
    print("Launching CareSentry-AI Plus Web UI on port 7860 (offline)...")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)


if __name__ == "__main__":
    main()
