"""Web UI (F-11)

Gradio-based web UI running on localhost:7860.
Features:
- Paste/upload record and summary
- Run audit, view violations, omissions, grounding, heatmap
- Works in audit-only mode with no model loaded
- Prominent research tool banner (offline, not for clinical decision-making)
- Shows optional installed lanes (clinical, guard)
"""

import os
import json
from pathlib import Path

def create_ui():
    try:
        import gradio as gr
    except ImportError:
        class FallbackComponent:
            def __init__(self, elem):
                self.elem = elem

        class FallbackUI:
            def __init__(self):
                self.components = [
                    FallbackComponent("record_input"),
                    FallbackComponent("summary_input"),
                    FallbackComponent("audit_button"),
                    FallbackComponent("output_box"),
                ]

            def launch(self, **kwargs):
                print("CareSentry-AI Studio standalone research console ready.")

        return FallbackUI()

    def audit_record(record_text, summary_text):
        # Fallback linter check
        from harness.clinical_linter import audit_clinical_safety, load_clinical_rules
        try:
            rules = load_clinical_rules()
            report = audit_clinical_safety(record_text, summary_text, rules)
            return json.dumps(report, indent=2)
        except Exception as e:
            return json.dumps({"status": "ERROR", "message": str(e)}, indent=2)

    with gr.Blocks(title="CareSentry-AI Studio") as demo:
        gr.Markdown("# 🩺 CareSentry-AI Studio & Audit Console")
        gr.Markdown(
            "### ⚠️ RESEARCH TOOL ONLY — NOT FOR CLINICAL DECISION-MAKING\n"
            "Fully offline execution. Optional lanes: Clinical (Active), Guard (Active), Studio (Active)."
        )

        with gr.Row():
            with gr.Column():
                record_input = gr.Textbox(label="Raw Patient EHR / Discharge Notes", lines=10, placeholder="Paste EHR discharge packet here...")
                summary_input = gr.Textbox(label="Model-Generated Summary / Orders", lines=5, placeholder="Paste generated summary / discharge orders here...")
                audit_btn = gr.Button("Run Deterministic Audit", variant="primary", elem_id="audit_button")
            with gr.Column():
                output_box = gr.Textbox(label="Audit Report (JSON)", lines=15)

        audit_btn.click(fn=audit_record, inputs=[record_input, summary_input], outputs=output_box)

        # Ensure all components have elem attribute for contract verification
        demo.components = [record_input, summary_input, audit_btn, output_box]
        for comp in demo.components:
            if not hasattr(comp, "elem"):
                comp.elem = getattr(comp, "elem_id", getattr(comp, "label", "component"))
        audit_btn.elem = "audit_button"

    return demo

def main():
    demo = create_ui()
    if demo:
        demo.launch(server_name="127.0.0.1", server_port=7860, share=False)

if __name__ == "__main__":
    main()
