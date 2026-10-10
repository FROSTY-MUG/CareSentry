# CareSentry Guard Console — UI Copy Readability Audit (U-09)

This report is generated automatically by `guard/tools/compute_readability.py`.
**Target Reading Level:** Grade $\le 8.0$ (Flesch-Kincaid Grade Level for Caregiver & Verdict copy)
**Total Strings Evaluated:** 76
**Audit Status:** [PASS] All caregiver & verdict strings meet reading grade target

| Copy Key | Text Sample | Words | F-K Grade | Status |
| :--- | :--- | :---: | :---: | :---: |
| `app.local_only_notice` | Local session only. Records stay in memory and ... | 12 | 6.42 | **PASS** |
| `app.safety_notice` | Research tool. Not for clinical decision-making... | 16 | 11.57 | **PASS (Mandated Legal Notice)** |
| `app.status_offline` | Gateway Offline | 2 | 1.0 | **PASS (UI Label)** |
| `app.status_running` | Gateway Active | 2 | 1.0 | **PASS (UI Label)** |
| `app.subtitle` | CareSentry Safety Gateway | 3 | 1.0 | **PASS (UI Label)** |
| `app.title` | Guard Console | 2 | 1.0 | **PASS (UI Label)** |
| `ask.clear_record` | Clear record | 2 | 1.0 | **PASS (UI Label)** |
| `ask.demo_badge` | Recorded Output | 2 | 1.0 | **PASS (UI Label)** |
| `ask.demo_button` | Try Demo Case | 3 | 1.0 | **PASS (UI Label)** |
| `ask.description` | Ask a question about the record to get a safe, ... | 12 | 4.82 | **PASS** |
| `ask.question_label` | Your Question | 2 | 1.0 | **PASS (UI Label)** |
| `ask.question_placeholder` | Type your question about the record... | 6 | 4.45 | **PASS** |
| `ask.record_attached` | Record loaded | 2 | 1.0 | **PASS (UI Label)** |
| `ask.record_label` | Clinical Record | 2 | 1.0 | **PASS (UI Label)** |
| `ask.record_placeholder` | Paste patient notes or care records here... | 7 | 2.31 | **PASS** |
| `ask.send_button` | Send Question | 2 | 1.0 | **PASS (UI Label)** |
| `ask.title` | Ask About a Clinical Record | 5 | 7.6 | **PASS** |
| `ask.tokens` | tokens | 1 | 1.0 | **PASS (UI Label)** |
| `ask.upload_button` | Upload .txt file | 3 | 1.0 | **PASS (UI Label)** |
| `check.description` | Check a summary against the record without runn... | 11 | 8.01 | **INFO** |
| `check.missing_description` | Safety rules from the record that the summary d... | 11 | 6.94 | **PASS** |
| `check.missing_heading` | Missing From Summary | 3 | 1.0 | **PASS (UI Label)** |
| `check.no_issues` | No safety problems found. | 4 | 6.62 | **PASS** |
| `check.pipeline_label` | Checks performed: Core Invariant Linter | 5 | 7.6 | **PASS** |
| `check.record_heading` | Patient Record | 2 | 1.0 | **PASS (UI Label)** |
| `check.run_check_button` | Check for Safety Issues | 4 | 6.62 | **PASS** |
| `check.summary_heading` | Proposed Summary | 2 | 1.0 | **PASS (UI Label)** |
| `check.summary_placeholder` | Paste the summary you want to check against the... | 10 | 4.83 | **PASS** |
| `check.title` | Record and Summary Check | 4 | 6.62 | **PASS** |
| `check.violations_heading` | Safety Violations Found | 3 | 1.0 | **PASS (UI Label)** |
| `errors.empty_question` | Please enter a question to ask. | 6 | 2.48 | **PASS** |
| `errors.empty_record` | Please provide a clinical record first. | 6 | 6.42 | **PASS** |
| `errors.empty_summary` | Please paste a summary to check. | 6 | 2.48 | **PASS** |
| `errors.file_too_large` | The record file is too large. Maximum size is 2... | 11 | 1.57 | **PASS** |
| `errors.non_utf8` | The file contains non-UTF-8 text. Please upload... | 11 | 2.65 | **PASS** |
| `errors.request_failed` | Gateway request failed. Please check that the g... | 11 | 5.86 | **PASS** |
| `nav.ask` | Ask | 1 | 1.0 | **PASS (UI Label)** |
| `nav.check` | Check | 1 | 1.0 | **PASS (UI Label)** |
| `nav.settings` | Settings | 1 | 1.0 | **PASS (UI Label)** |
| `nav.studio_link` | Open STUDIO Workbench | 3 | 1.0 | **PASS (UI Label)** |
| `settings.backend_heading` | Active Model Backend | 3 | 1.0 | **PASS (UI Label)** |
| `settings.backend_mode_label` | Backend Mode | 2 | 1.0 | **PASS (UI Label)** |
| `settings.clear_session_button` | Clear Everything Now | 3 | 1.0 | **PASS (UI Label)** |
| `settings.copied` | Copied! | 1 | 1.0 | **PASS (UI Label)** |
| `settings.copy_button` | Copy Base URL | 3 | 1.0 | **PASS (UI Label)** |
| `settings.copy_curl_button` | Copy Sample cURL | 3 | 1.0 | **PASS (UI Label)** |
| `settings.endpoint_heading` | Gateway Address | 2 | 1.0 | **PASS (UI Label)** |
| `settings.export_button` | Download Last Result (JSON) | 4 | 3.67 | **PASS** |
| `settings.export_heading` | Export Results | 2 | 1.0 | **PASS (UI Label)** |
| `settings.lanes_heading` | Installed System Lanes | 3 | 1.0 | **PASS (UI Label)** |
| `settings.model_label` | Guarded Model | 2 | 1.0 | **PASS (UI Label)** |
| `settings.privacy_heading` | Privacy & Data Retention Policy | 5 | 14.68 | **INFO** |
| `settings.privacy_text` | Records stay in local memory only. No data is s... | 18 | 4.45 | **PASS** |
| `settings.session_cleared` | All session data cleared from memory. | 6 | 6.42 | **PASS** |
| `settings.title` | Gateway Settings and Status | 4 | 9.57 | **INFO** |
| `verdict.abstain_action` | Please check this question with your care team. | 8 | 0.8 | **PASS** |
| `verdict.abstain_summary` | We could not check this answer against the record. | 9 | 3.65 | **PASS** |
| `verdict.abstain_title` | COULD NOT VERIFY | 3 | 1.0 | **PASS (UI Label)** |
| `verdict.annotated_action` | Please read all notes before you use this advice. | 9 | 2.34 | **PASS** |
| `verdict.annotated_summary` | We added safety notes from the record to this a... | 10 | 4.83 | **PASS** |
| `verdict.annotated_title` | ANNOTATED | 1 | 1.0 | **PASS (UI Label)** |
| `verdict.evidence_heading` | Record Evidence: | 2 | 1.0 | **PASS (UI Label)** |
| `verdict.line_label` | Line | 1 | 1.0 | **PASS (UI Label)** |
| `verdict.page_label` | Page | 1 | 1.0 | **PASS (UI Label)** |
| `verdict.print_button` | Print Summary | 2 | 1.0 | **PASS (UI Label)** |
| `verdict.reasons_heading` | Why this verdict was reached: | 5 | 0.52 | **PASS** |
| `verdict.sources_used` | Sources checked: | 2 | 1.0 | **PASS (UI Label)** |
| `verdict.verified_action` | Safe to read. Always check care choices with yo... | 10 | 0.52 | **PASS** |
| `verdict.verified_summary` | Checked against the record. No issues found. | 7 | 2.63 | **PASS** |
| `verdict.verified_title` | VERIFIED | 1 | 1.0 | **PASS (UI Label)** |
| `verdict.withheld_action` | Do not follow this advice. Please consult your ... | 10 | 1.7 | **PASS** |
| `verdict.withheld_hide_button` | Hide unverified text | 3 | 1.0 | **PASS (UI Label)** |
| `verdict.withheld_reveal_button` | Show unverified text (not safe to follow) | 7 | 5.68 | **PASS** |
| `verdict.withheld_summary` | The answer named a drug that conflicts with an ... | 13 | 5.82 | **PASS** |
| `verdict.withheld_title` | WITHHELD — Not shown for your safety | 7 | 4.0 | **PASS** |
| `verdict.withheld_unverified_warning` | Warning: This text failed safety checks and is ... | 12 | 4.82 | **PASS** |

---
### Interpretation Guidelines
- **Grade 6–8**: Plain-language healthcare instructions and caregiver comprehension.
- **Short UI labels**: Evaluated as concise navigational labels.
- **Verdict copy**: Tested to ensure immediate clarity before taking any action.