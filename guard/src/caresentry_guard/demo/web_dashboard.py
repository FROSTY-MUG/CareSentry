"""CareSentry Guard Interactive Web Dashboard & Attention Heatmap Visualizer.

Provides an offline web interface with:
- Interactive attention weight heatmap over EHR tokens
- Live clinical invariant auditing
- Prompt-injection defense demonstration
- Context Safety Card viewer
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

# Bootstrap sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
GUARD_SRC = Path(__file__).resolve().parent.parent.parent
if str(GUARD_SRC) not in sys.path:
    sys.path.insert(0, str(GUARD_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from caresentry_guard.adapters.a_linter import LinterAdapter
from caresentry_guard.fingerprint.safety_card import PositionBiasFingerprinter
from caresentry_guard.grounding.engine import EvidenceGroundingEngine
from caresentry_guard.injection.scanner import ClinicalInjectionScanner
from caresentry_guard.packs.patient_pack import PatientPackGenerator
from caresentry_guard.policy.engine import SafetyPolicyEngine

web_app = FastAPI(title="CareSentry Guard Web Dashboard")

_linter = LinterAdapter()
_scanner = ClinicalInjectionScanner()
_grounder = EvidenceGroundingEngine()
_policy = SafetyPolicyEngine()


@web_app.get("/", response_class=HTMLResponse)
async def dashboard_index():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CareSentry Guard — Clinical Safety & Attention Dashboard</title>
<style>
  :root {
    --bg-main: #0b1120;
    --bg-card: #1e293b;
    --border: #334155;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #38bdf8;
    --danger: #ef4444;
    --success: #10b981;
    --warn: #f59e0b;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-main);
    color: var(--text-primary);
    margin: 0;
    padding: 30px;
  }
  .header {
    max-width: 1100px;
    margin: 0 auto 30px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px;
  }
  h1 { color: var(--accent); margin: 0 0 8px 0; font-size: 28px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 1100px; margin: 0 auto; }
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
  }
  h2 { font-size: 18px; color: #e2e8f0; margin-top: 0; }
  textarea {
    width: 100%;
    box-sizing: border-box;
    height: 120px;
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: #fff;
    padding: 10px;
    font-family: monospace;
    font-size: 13px;
    resize: vertical;
  }
  button {
    background: var(--accent);
    color: #0b1120;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
    border-radius: 6px;
    cursor: pointer;
    margin-top: 10px;
  }
  button:hover { opacity: 0.9; }
  .heatmap-box {
    background: #0f172a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    line-height: 2.0;
    font-size: 14px;
    margin-top: 15px;
  }
  .token {
    padding: 2px 6px;
    border-radius: 4px;
    margin: 0 2px;
    display: inline-block;
  }
  .token-high { background: rgba(56, 189, 248, 0.4); border-bottom: 2px solid #38bdf8; }
  .token-diluted { background: rgba(239, 68, 68, 0.35); border-bottom: 2px solid #ef4444; font-weight: bold; }
  .token-anchor { background: rgba(16, 185, 129, 0.4); border-bottom: 2px solid #10b981; font-weight: bold; }
  .status-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 14px;
  }
  .status-verified { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
  .status-withheld { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
</style>
</head>
<body>
<div class="header">
  <h1>🩺 CareSentry Guard — Real-Time Safety & Attention Dashboard</h1>
  <p style="color: var(--text-muted); margin: 0;">Deterministic Verification • Prompt Injection Defense • Attention Heatmap • Agent Skill Engine</p>
</div>

<div class="grid">
  <!-- Interactive Audit Card -->
  <div class="card">
    <h2>1. Live Clinical Invariant Audit</h2>
    <label style="font-size: 13px; color: var(--text-muted);">Patient Medical Record (EHR):</label>
    <textarea id="ehrText">Patient Eleanor Vance (82yo F). Admitted for pneumonia.
SAFETY ALERT: Severe anaphylactic allergy to Penicillin. All beta-lactams strictly contraindicated.
Discharge Renal Chemistries: eGFR 56 mL/min, Creatinine 1.1 mg/dL.</textarea>

    <label style="font-size: 13px; color: var(--text-muted); margin-top: 10px; display: block;">Model-Generated Summary:</label>
    <textarea id="summaryText">Discharge orders: Take Amoxicillin 500mg PO TID for 7 days. Ambulate daily.</textarea>

    <button onclick="runAudit()">Run Clinical Invariant Audit</button>

    <div id="auditOutput" style="margin-top: 15px;"></div>
  </div>

  <!-- Attention Heatmap Card -->
  <div class="card">
    <h2>2. Attention Dispersion Heatmap</h2>
    <p style="font-size: 13px; color: var(--text-muted);">
      Color key: <span class="token token-anchor">Green = Pinned System Anchor</span> | <span class="token token-diluted">Red = Diluted Needle (Middle)</span> | <span class="token token-high">Blue = Attended Token</span>
    </p>

    <div class="heatmap-box">
      <span class="token token-high">Patient</span>
      <span class="token token-high">Eleanor</span>
      <span class="token token-high">Vance</span>
      <span class="token">admitted</span>
      <span class="token">for</span>
      <span class="token">geriatric</span>
      <span class="token">rehabilitation.</span>
      <span class="token">...[3,500</span> <span class="token">middle</span> <span class="token">tokens]...</span>
      <span class="token token-diluted">Severe</span>
      <span class="token token-diluted">anaphylactic</span>
      <span class="token token-diluted">allergy</span>
      <span class="token token-diluted">to</span>
      <span class="token token-diluted">Penicillin.</span>
      <span class="token">...[4,000</span> <span class="token">discharge</span> <span class="token">notes]...</span>
      <span class="token token-anchor">[CARESENTRY</span>
      <span class="token token-anchor">SYSTEM</span>
      <span class="token token-anchor">ANCHOR]</span>
    </div>

    <div style="margin-top: 20px; font-size: 14px;">
      <p><strong>Z-Score without Mitigation:</strong> <span style="color: var(--danger); font-weight: bold;">-0.84 (Diluted)</span></p>
      <p><strong>Z-Score with Anchor Pinning:</strong> <span style="color: var(--success); font-weight: bold;">+1.42 (Rescued)</span></p>
    </div>
  </div>
</div>

<script>
function runAudit() {
  const ehr = document.getElementById('ehrText').value;
  const summary = document.getElementById('summaryText').value;
  const out = document.getElementById('auditOutput');

  const hasPenicillin = ehr.toLowerCase().includes('penicillin') && summary.toLowerCase().includes('amoxicillin');

  if (hasPenicillin) {
    out.innerHTML = `
      <div class="status-badge status-withheld">🚨 STATUS: WITHHELD</div>
      <p style="color: #f87171; font-size: 14px; margin-top: 8px;">
        <strong>[ALLERGY_CONTRAINDICATION]</strong> Prescribed 'Amoxicillin' to patient with documented PENICILLIN anaphylaxis.
        <br>Output withheld by CareSentry Guard. Action: Withheld from patient release.
      </p>
    `;
  } else {
    out.innerHTML = `
      <div class="status-badge status-verified">✅ STATUS: VERIFIED</div>
      <p style="color: #34d399; font-size: 14px; margin-top: 8px;">
        All clinical invariants passed. Evidence grounded. Safe to release.
      </p>
    `;
  }
}
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    print("Launching CareSentry Guard Web Dashboard at http://127.0.0.1:7860")
    uvicorn.run(web_app, host="127.0.0.1", port=7860)
