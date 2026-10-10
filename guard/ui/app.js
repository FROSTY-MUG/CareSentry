/**
 * CareSentry-AI Guard Console — Track C Client Application
 * Plain Vanilla JavaScript, Zero External Dependencies, Offline-First.
 */

(function () {
  'use strict';

  // Global Session and State
  let sessionId = null;
  let currentRecord = '';
  let lastAuditResult = null;
  let isDemoActive = false;

  // DOM Elements
  const tabAsk = document.getElementById('tabAsk');
  const tabCheck = document.getElementById('tabCheck');
  const tabAttention = document.getElementById('tabAttention');
  const tabSettings = document.getElementById('tabSettings');
  const panelAsk = document.getElementById('panelAsk');
  const panelCheck = document.getElementById('panelCheck');
  const panelAttention = document.getElementById('panelAttention');
  const panelSettings = document.getElementById('panelSettings');
  const attentionCanvas3D = document.getElementById('attentionCanvas3D');
  const btnModeDiluted = document.getElementById('btnModeDiluted');
  const btnModeAnchored = document.getElementById('btnModeAnchored');
  const btnModeReordered = document.getElementById('btnModeReordered');
  const visualizerModelSelect = document.getElementById('visualizerModelSelect');
  const btnResetCamera = document.getElementById('btnResetCamera');
  const decisionLayersDesc = document.getElementById('decisionLayersDesc');
  const remediationDesc = document.getElementById('remediationDesc');
  let attentionVisualizer = null;

  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const studioWorkbenchLink = document.getElementById('studioWorkbenchLink');

  const recordInput = document.getElementById('recordInput');
  const recordStatusBadge = document.getElementById('recordStatusBadge');
  const demoBadge = document.getElementById('demoBadge');
  const clearRecordBtn = document.getElementById('clearRecordBtn');
  const uploadFileBtn = document.getElementById('uploadFileBtn');
  const recordFileInput = document.getElementById('recordFileInput');
  const recordUploadMsg = document.getElementById('recordUploadMsg');

  const questionInput = document.getElementById('questionInput');
  const sendBtn = document.getElementById('sendBtn');
  const demoBtn = document.getElementById('demoBtn');
  const chatTimeline = document.getElementById('chatTimeline');

  const checkRecordInput = document.getElementById('checkRecordInput');
  const checkSummaryInput = document.getElementById('checkSummaryInput');
  const runCheckBtn = document.getElementById('runCheckBtn');
  const checkResultsContainer = document.getElementById('checkResultsContainer');

  const settingsModelId = document.getElementById('settingsModelId');
  const settingsBackendMode = document.getElementById('settingsBackendMode');
  const settingsVersion = document.getElementById('settingsVersion');
  const installedLanesContainer = document.getElementById('installedLanesContainer');
  const copyUrlBtn = document.getElementById('copyUrlBtn');
  const copyCurlBtn = document.getElementById('copyCurlBtn');
  const clearSessionBtn = document.getElementById('clearSessionBtn');
  const exportResultBtn = document.getElementById('exportResultBtn');
  const sessionStatusMsg = document.getElementById('sessionStatusMsg');
  const printTimestamp = document.getElementById('printTimestamp');

  // --- 1. Tab Navigation ---
  function initTabs() {
    const tabs = [
      { btn: tabAsk, panel: panelAsk },
      { btn: tabCheck, panel: panelCheck },
      { btn: tabAttention, panel: panelAttention },
      { btn: tabSettings, panel: panelSettings }
    ];

    tabs.forEach(({ btn, panel }) => {
      if (!btn || !panel) return;
      btn.addEventListener('click', () => {
        tabs.forEach(t => {
          if (t.btn) {
            t.btn.classList.remove('active');
            t.btn.setAttribute('aria-selected', 'false');
          }
          if (t.panel) {
            t.panel.classList.remove('active');
          }
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        panel.classList.add('active');

        if (btn === tabAttention && attentionVisualizer) {
          setTimeout(() => {
            attentionVisualizer.resize();
            attentionVisualizer.render();
          }, 60);
        }
      });
    });
  }

  // --- 2. Session Management ---
  async function initSession() {
    try {
      const res = await fetch('/ui/api/session', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        sessionId = data.session_id;
      }
    } catch (err) {
      console.warn('Could not initialize session with gateway:', err);
    }
  }

  function clearSession() {
    if (sessionId) {
      try {
        navigator.sendBeacon('/ui/api/session', JSON.stringify({ session_id: sessionId }));
      } catch (e) {
        fetch('/ui/api/session', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
          keepalive: true
        });
      }
    }
    sessionId = null;
    currentRecord = '';
    lastAuditResult = null;
    isDemoActive = false;
    recordInput.value = '';
    questionInput.value = '';
    chatTimeline.innerHTML = '';
    updateRecordBadge();
    if (sessionStatusMsg) {
      sessionStatusMsg.textContent = 'Session data cleared from memory.';
      setTimeout(() => { sessionStatusMsg.textContent = ''; }, 3000);
    }
  }

  window.addEventListener('pagehide', () => {
    if (sessionId) {
      navigator.sendBeacon('/ui/api/session', JSON.stringify({ session_id: sessionId }));
    }
  });

  // --- 3. Gateway Status & Lanes ---
  async function fetchStatus() {
    try {
      const res = await fetch('/ui/api/status');
      if (res.ok) {
        const data = await res.json();
        statusDot.classList.remove('offline');
        statusText.textContent = `Active (${data.model_id || 'Guarded'})`;
        if (settingsModelId) settingsModelId.textContent = data.model_id || 'Qwen/Qwen2.5-1.5B-Instruct';
        if (settingsBackendMode) settingsBackendMode.textContent = data.backend_mode || 'Deterministic Safety Policy';
        if (settingsVersion) settingsVersion.textContent = data.version || '1.0.0';

        renderInstalledLanes(data.installed_lanes || {});
        if (data.studio_active && studioWorkbenchLink) {
          studioWorkbenchLink.style.display = 'inline';
        }
      } else {
        markOffline();
      }
    } catch (e) {
      markOffline();
    }
  }

  function markOffline() {
    statusDot.classList.add('offline');
    statusText.textContent = 'Gateway Offline';
  }

  function renderInstalledLanes(lanes) {
    if (!installedLanesContainer) return;
    const laneKeys = [
      { id: 'core', label: 'Track A (Core Invariant Engine)' },
      { id: 'clinical', label: 'Track B (Clinical Validation Rules)' },
      { id: 'guard', label: 'Track C (CareSentry Guard Gateway)' },
      { id: 'studio', label: 'Track D (STUDIO Workbench)' }
    ];

    let html = '<div style="display:flex; flex-direction:column; gap:8px;">';
    laneKeys.forEach(l => {
      const isInstalled = !!lanes[l.id];
      const badgeStyle = isInstalled
        ? 'background:rgba(46,160,67,0.15); color:#3fb950; border:1px solid #2ea043;'
        : 'background:rgba(139,148,158,0.1); color:#8b949e; border:1px solid #30363d;';
      const mark = isInstalled ? '&#10003; INSTALLED' : '&mdash; NOT INSTALLED';

      html += `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid var(--border-subtle);">
          <span>${l.label}</span>
          <span style="font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; ${badgeStyle}">${mark}</span>
        </div>
      `;
    });
    html += '</div>';
    installedLanesContainer.innerHTML = html;
  }

  // --- 4. Record Handling ---
  function updateRecordBadge() {
    const text = recordInput.value.trim();
    currentRecord = text;
    if (text) {
      const wordCount = text.split(/\s+/).length;
      const tokenEst = Math.round(wordCount * 1.3);
      recordStatusBadge.textContent = `Record: Attached (~${tokenEst} tokens)`;
      clearRecordBtn.style.display = 'inline-block';
      if (isDemoActive) {
        demoBadge.style.display = 'inline-block';
      } else {
        demoBadge.style.display = 'none';
      }
    } else {
      recordStatusBadge.textContent = 'Record: Not attached';
      clearRecordBtn.style.display = 'none';
      demoBadge.style.display = 'none';
    }
  }

  recordInput.addEventListener('input', () => {
    isDemoActive = false;
    updateRecordBadge();
  });

  clearRecordBtn.addEventListener('click', () => {
    recordInput.value = '';
    isDemoActive = false;
    updateRecordBadge();
  });

  uploadFileBtn.addEventListener('click', () => {
    recordFileInput.click();
  });

  recordFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      recordUploadMsg.textContent = 'File too large (limit 2 MB).';
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      recordInput.value = event.target.result;
      recordUploadMsg.textContent = `Loaded ${file.name}`;
      isDemoActive = false;
      updateRecordBadge();
    };
    reader.onerror = () => {
      recordUploadMsg.textContent = 'Failed to read file.';
    };
    reader.readAsText(file, 'UTF-8');
  });

  // --- 5. Ask View & Verdict Rendering (U-02, U-10) ---
  sendBtn.addEventListener('click', handleSendQuestion);
  questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuestion();
    }
  });

  async function handleSendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    const record = recordInput.value.trim();
    if (!record) {
      alert('Please attach or paste a patient record first.');
      return;
    }

    // Append user query message card
    appendUserMessage(question);
    questionInput.value = '';

    // Show temporary loading indicator
    const loadingCard = document.createElement('div');
    loadingCard.className = 'card';
    loadingCard.innerHTML = '<p style="color:var(--text-muted);">Evaluating clinical invariants and running safety policies...</p>';
    chatTimeline.appendChild(loadingCard);
    chatTimeline.scrollTop = chatTimeline.scrollHeight;

    try {
      const res = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'Qwen/Qwen2.5-1.5B-Instruct',
          messages: [{ role: 'user', content: question }],
          clinical_record: record
        })
      });

      loadingCard.remove();

      if (!res.ok) {
        throw new Error(`Gateway returned HTTP ${res.status}`);
      }

      const data = await res.json();
      lastAuditResult = data;
      renderVerdictCard(data, question);
    } catch (err) {
      loadingCard.remove();
      renderErrorCard('Could not verify. Do not rely on this answer. Gateway error occurred.');
    }
  }

  function appendUserMessage(text) {
    const card = document.createElement('div');
    card.className = 'user-query-card';
    card.innerHTML = `
      <div class="user-query-author">You asked:</div>
      <div class="user-query-text">${escapeHtml(text)}</div>
    `;
    chatTimeline.appendChild(card);
  }

  function renderVerdictCard(completionData, queryText) {
    const caresentry = completionData.caresentry || {};
    const state = (caresentry.policy_state || 'ABSTAIN').toUpperCase();
    const assistantMessage = completionData.choices?.[0]?.message?.content || '';
    const reasons = caresentry.reasons || [];
    const auditMeta = caresentry.audit_metadata || {};

    const card = document.createElement('div');
    card.className = `verdict-card ${state.toLowerCase()}`;
    card.setAttribute('role', state === 'WITHHELD' ? 'alert' : 'status');

    let stateTitle = '';
    let stateSummary = '';
    let stateAction = '';
    let stateIcon = '';

    if (state === 'VERIFIED') {
      stateIcon = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>`;
      stateTitle = 'VERIFIED';
      stateSummary = 'Checked against the record. No issues found.';
      stateAction = 'Safe to read. Always verify critical care choices with your doctor.';
    } else if (state === 'ANNOTATED') {
      stateIcon = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      stateTitle = 'ANNOTATED';
      stateSummary = 'The answer was updated with important safety notes from the record.';
      stateAction = 'Please read the safety warnings before acting on this information.';
    } else if (state === 'WITHHELD') {
      stateIcon = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>`;
      stateTitle = 'WITHHELD — Not shown for your safety';
      stateSummary = 'The answer named a medicine that conflicts with a documented allergy or safety rule.';
      stateAction = 'Do not follow this advice. Please consult your care team.';
    } else {
      // ABSTAIN
      stateIcon = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      stateTitle = 'COULD NOT VERIFY';
      stateSummary = 'We could not verify this answer against the clinical record.';
      stateAction = 'Please confirm this question directly with your care team.';
    }

    let contentHtml = '';
    if (state === 'WITHHELD') {
      // U-02: WITHHELD never displays unverified text in default view!
      // Concealed behind a second, labeled button control.
      const unverifiedText = auditMeta.raw_summary || 'Unverified prescription or dosage recommendation.';
      contentHtml = `
        <div class="withheld-concealed-notice">
          <div class="withheld-concealed-title">&#9940; Medical advice withheld</div>
          <p style="font-size:0.95rem; margin-bottom:8px;">${escapeHtml(stateSummary)}</p>
          <p style="font-size:0.9rem; color:var(--text-secondary);"><strong>Action:</strong> ${escapeHtml(stateAction)}</p>
        </div>
        <div class="reveal-container">
          <button class="btn-secondary reveal-unverified-btn" type="button" aria-expanded="false">
            Show unverified text (not safe to follow)
          </button>
          <div class="unverified-revealed-text" style="display:none;" aria-hidden="true">
            <p style="font-size:0.85rem; font-weight:700; color:var(--state-withheld); margin-bottom:4px;">
              &#9888; Warning: This text failed safety checks and is not safe to follow:
            </p>
            <p class="raw-unverified-content">${escapeHtml(unverifiedText)}</p>
          </div>
        </div>
      `;
    } else {
      contentHtml = `
        <div class="verdict-content-box">
          <p style="font-size:1rem; line-height:1.6;">${escapeHtml(assistantMessage)}</p>
        </div>
      `;
    }

    // Reason & Evidence block
    let evidenceHtml = '';
    if (reasons.length > 0) {
      evidenceHtml += `
        <div class="verdict-details-pane">
          <strong>Why this verdict was reached:</strong>
          <ul style="margin: 6px 0 10px 20px; font-size:0.9rem;">
            ${reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="verdict-header">
        <div class="verdict-icon" aria-hidden="true">${stateIcon}</div>
        <div>
          <h2 class="verdict-title">${stateTitle}</h2>
          <div class="verdict-summary">${stateSummary}</div>
        </div>
      </div>
      <div class="verdict-action"><strong>Next step:</strong> ${stateAction}</div>
      ${contentHtml}
      ${evidenceHtml}
      <div style="margin-top:14px; display:flex; justify-content:space-between; align-items:center;">
        <button class="btn-secondary" onclick="window.print()" type="button">
          Print Summary
        </button>
        <span style="font-size:0.8rem; color:var(--text-muted);">Timestamp: ${new Date().toLocaleTimeString()}</span>
      </div>
    `;

    // Attach listener for reveal button if WITHHELD
    if (state === 'WITHHELD') {
      const revealBtn = card.querySelector('.reveal-unverified-btn');
      const textPane = card.querySelector('.unverified-revealed-text');
      revealBtn.addEventListener('click', () => {
        const isHidden = textPane.style.display === 'none';
        if (isHidden) {
          textPane.style.display = 'block';
          textPane.setAttribute('aria-hidden', 'false');
          revealBtn.setAttribute('aria-expanded', 'true');
          revealBtn.textContent = 'Hide unverified text';
        } else {
          textPane.style.display = 'none';
          textPane.setAttribute('aria-hidden', 'true');
          revealBtn.setAttribute('aria-expanded', 'false');
          revealBtn.textContent = 'Show unverified text (not safe to follow)';
        }
      });
    }

    chatTimeline.appendChild(card);
    chatTimeline.scrollTop = chatTimeline.scrollHeight;
  }

  function renderErrorCard(message) {
    const card = document.createElement('div');
    card.className = 'verdict-card withheld';
    card.setAttribute('role', 'alert');
    card.innerHTML = `
      <div class="verdict-header">
        <div class="verdict-icon">&#9888;</div>
        <div>
          <h2 class="verdict-title">VERIFICATION FAILED</h2>
          <div class="verdict-summary">${escapeHtml(message)}</div>
        </div>
      </div>
    `;
    chatTimeline.appendChild(card);
  }

  // --- 6. Demo Mode (U-10) ---
  demoBtn.addEventListener('click', () => {
    isDemoActive = true;
    const demoRecord = 
`PATIENT CLINICAL SUMMARY & DISCHARGE NOTE
Patient: John Doe | Age: 58 | MRN: #48291
Allergies: Documented severe anaphylactic reaction to Penicillin (Record Line 412).
Diagnoses: Acute bacterial pneumonia / lower respiratory tract infection.
Past Medical History: Hypertension, Asthma.
Attending Note: Do not prescribe beta-lactam class antibiotics due to history of anaphylaxis.`;

    const demoQuestion = "What antibiotic should I give for the chest infection?";

    recordInput.value = demoRecord;
    questionInput.value = demoQuestion;
    updateRecordBadge();

    // Trigger synthetic demo verdict
    appendUserMessage(demoQuestion);

    const syntheticWithheldResponse = {
      id: "chatcmpl-demo-synthetic",
      model: "Qwen/Qwen2.5-1.5B-Instruct [Recorded]",
      choices: [{
        index: 0,
        message: {
          role: "assistant",
          content: "[Withheld for patient safety: Suggested amoxicillin/clavulanate contradicts documented Penicillin allergy.]"
        }
      }],
      caresentry: {
        guard_version: "1.0.0",
        policy_state: "WITHHELD",
        is_safe_to_release: false,
        reasons: [
          "Documented anaphylactic reaction to Penicillin allergy (Record Line 412, p.1)",
          "Model proposed Amoxicillin (cross-reactive beta-lactam)",
          "Linter Invariant 1 violated: Severe Allergy Conflict"
        ],
        escalate_to_human: true,
        audit_metadata: {
          raw_summary: "For this bacterial chest infection, initiate Amoxicillin 500mg PO TID for 7 days.",
          evidence_span: "Documented severe anaphylactic reaction to Penicillin"
        }
      }
    };

    lastAuditResult = syntheticWithheldResponse;
    renderVerdictCard(syntheticWithheldResponse, demoQuestion);
  });

  // --- 7. Check Screen (U-04) ---
  runCheckBtn.addEventListener('click', async () => {
    const record = checkRecordInput.value.trim();
    const summary = checkSummaryInput.value.trim();

    if (!record || !summary) {
      alert('Please provide both the clinical record and the proposed summary to check.');
      return;
    }

    runCheckBtn.disabled = true;
    runCheckBtn.textContent = 'Running Linter Pipeline...';
    checkResultsContainer.style.display = 'none';

    try {
      const res = await fetch('/ui/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ record, summary })
      });

      const data = await res.json();
      renderCheckResults(data);
    } catch (e) {
      alert('Failed to execute audit check.');
    } finally {
      runCheckBtn.disabled = false;
      runCheckBtn.textContent = 'Check for Safety Issues';
    }
  });

  function renderCheckResults(data) {
    checkResultsContainer.innerHTML = '';
    checkResultsContainer.style.display = 'block';

    const violations = data.violations || [];
    const missingItems = data.missing_constraints || [];

    let html = `
      <div class="card" style="margin-top:20px;">
        <h3 class="card-title">Audit Results &bull; Status: ${escapeHtml(data.status)}</h3>
        <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:12px;">
          Checks performed: Core Invariant Linter (Deterministic, no model needed).
        </p>
    `;

    if (violations.length === 0 && missingItems.length === 0) {
      html += `
        <div style="padding:16px; background:rgba(46,160,67,0.1); border:1px solid var(--state-verified-border); border-radius:6px; color:#3fb950; font-weight:600;">
          &#10003; No safety violations or omissions detected between record and summary.
        </div>
      `;
    } else {
      if (violations.length > 0) {
        html += `
          <h4 style="margin-top:12px; color:var(--state-withheld);">&#9888; Identified Safety Violations:</h4>
          <ul style="margin: 8px 0 16px 20px; font-size:0.95rem;">
            ${violations.map(v => `
              <li style="margin-bottom:6px;">
                <strong>${escapeHtml(v.type || 'Violation')}:</strong> ${escapeHtml(v.message || '')}
                ${v.record_line ? `<span class="evidence-tag">Record Line: ${v.record_line}</span>` : ''}
              </li>
            `).join('')}
          </ul>
        `;
      }

      if (missingItems.length > 0) {
        html += `
          <div class="missing-box">
            <div class="missing-title">&#10071; Missing from Summary (Critical Record Constraints):</div>
            <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">
              The record explicitly specifies the following constraints, which were omitted from the proposed summary:
            </p>
            <ul style="margin-left: 20px; font-size:0.9rem;">
              ${missingItems.map(m => `
                <li style="margin-bottom:4px;">
                  ${escapeHtml(m.constraint || m)}
                  ${m.record_line ? `<span class="evidence-tag">Line ${m.record_line}</span>` : ''}
                </li>
              `).join('')}
            </ul>
          </div>
        `;
      }
    }

    html += `</div>`;
    checkResultsContainer.innerHTML = html;
  }

  // --- 8. Settings & Utilities ---
  if (copyUrlBtn) {
    copyUrlBtn.addEventListener('click', () => {
      navigator.clipboard.writeText('http://127.0.0.1:8787/v1');
      copyUrlBtn.textContent = 'Copied!';
      setTimeout(() => { copyUrlBtn.textContent = 'Copy Base URL'; }, 2000);
    });
  }

  if (copyCurlBtn) {
    copyCurlBtn.addEventListener('click', () => {
      const snippet = document.getElementById('curlSnippet').innerText;
      navigator.clipboard.writeText(snippet);
      copyCurlBtn.textContent = 'Copied!';
      setTimeout(() => { copyCurlBtn.textContent = 'Copy Sample cURL'; }, 2000);
    });
  }

  if (clearSessionBtn) {
    clearSessionBtn.addEventListener('click', clearSession);
  }

  if (exportResultBtn) {
    exportResultBtn.addEventListener('click', () => {
      if (!lastAuditResult) {
        alert('No audit results available in current session to export.');
        return;
      }
      // Export sanitized result (raw record excluded per U-07)
      const exportData = {
        schema: "guard_audit_result.v1",
        exported_at: new Date().toISOString(),
        model: lastAuditResult.model,
        caresentry: lastAuditResult.caresentry,
        usage: lastAuditResult.usage
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `caresentry-guard-audit-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function initAttentionVisualizer() {
    if (!attentionCanvas3D || typeof AttentionVisualizer3D === 'undefined') return;
    try {
      attentionVisualizer = new AttentionVisualizer3D(attentionCanvas3D);
      window.visualizer = attentionVisualizer;

      const modeButtons = [
        { btn: btnModeDiluted, mode: 'diluted' },
        { btn: btnModeAnchored, mode: 'anchored' },
        { btn: btnModeReordered, mode: 'reordered' },
      ];

      modeButtons.forEach(({ btn, mode }) => {
        if (!btn) return;
        btn.addEventListener('click', () => {
          modeButtons.forEach(b => {
            if (b.btn) {
              b.btn.classList.remove('active');
              b.btn.style.boxShadow = 'none';
            }
          });
          btn.classList.add('active');
          btn.style.boxShadow = '0 0 10px rgba(88, 166, 255, 0.4)';
          attentionVisualizer.setMode(mode);

          if (mode === 'diluted') {
            if (decisionLayersDesc) {
              decisionLayersDesc.innerHTML = 'In standard unmitigated prompts over 10k tokens, attention to critical middle constraints (e.g., Penicillin allergy, eGFR &lt; 30) dilutes below background noise (<strong style="color:var(--state-withheld);">Z = -1.74</strong>). The model generates contraindicated medications with high fluency.';
            }
            if (remediationDesc) {
              remediationDesc.innerHTML = 'Unmitigated mode: Terminal decision layers are starved of constraint tokens, producing catastrophic hallucinations despite polite tone.';
            }
          } else if (mode === 'anchored') {
            if (decisionLayersDesc) {
              decisionLayersDesc.innerHTML = 'Terminal decision layers receive strongly amplified attention signals (<strong style="color:var(--state-verified);">Z = +38.27</strong>). Self-attention weights remain anchored across the generation step.';
            }
            if (remediationDesc) {
              remediationDesc.innerHTML = 'CareSentry Attention-Anchoring injects verified constraint prompts into the terminal decision boundary, mathematically elevating cross-head attention and preventing catastrophic clinical hallucination.';
            }
          } else {
            if (decisionLayersDesc) {
              decisionLayersDesc.innerHTML = 'Recency reordering moves constraints to the prompt suffix, restoring decision layer focus (<strong style="color:var(--focus-ring);">Z = +30.63</strong>) via natural recency bias.';
            }
            if (remediationDesc) {
              remediationDesc.innerHTML = 'Reordered mode: Effective for short-to-medium sequences, though Attention-Anchoring Gate remains optimal for &gt;16k token contexts.';
            }
          }
        });
      });

      if (visualizerModelSelect) {
        visualizerModelSelect.addEventListener('change', (e) => {
          const val = e.target.value;
          if (val.includes('1.5B')) {
            attentionVisualizer.setModel(val, 28, 12);
          } else if (val.includes('0.5B')) {
            attentionVisualizer.setModel(val, 24, 14);
          } else if (val.includes('gemma')) {
            attentionVisualizer.setModel(val, 26, 8);
          } else if (val.includes('Llama')) {
            attentionVisualizer.setModel(val, 16, 32);
          }
        });
      }

      if (btnResetCamera) {
        btnResetCamera.addEventListener('click', () => {
          attentionVisualizer.resetCamera();
        });
      }
    } catch (err) {
      console.warn('Failed to initialize AttentionVisualizer3D:', err);
    }
  }

  // Set print timestamp
  if (printTimestamp) {
    printTimestamp.textContent = `Report generated on ${new Date().toLocaleString()}`;
  }

  // Initialize on load
  initTabs();
  initSession();
  fetchStatus();
  initAttentionVisualizer();
})();
