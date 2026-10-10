# Handoff Request B-0005: Mention `plus/README_PLUS.md` in Main README

**From:** Track B (Antigravity IDE-B)  
**To:** Track A (Core Harness IDE-A)  
**Status:** Open / Proposed at Checkpoint 1  
**Category:** Documentation Coordination  

## Summary
In `README.md`, add a dedicated section or badge linking to `plus/README_PLUS.md` for users and evaluators seeking the extended clinical invariant suite, omission checker, attention heatmap viewer, and web UI.

## Rationale
Per the ownership matrix (Section 3.1), Track A owns root `README.md` and Track B never edits it directly.

## Proposed Snippet (For Track A to paste into README.md)
```markdown
## CareSentry-AI Plus (Extended Track)
For extended invariant rule packs (geriatric Beers criteria, dose-aware Cockcroft-Gault/CKD-EPI, cross-reactivity), reverse omission checking, interactive token attention heatmaps, and local Gradio web UI, see [CareSentry-AI Plus](plus/README_PLUS.md).
```

## Track B Fallback While Waiting
Track B documents its features completely in `plus/README_PLUS.md`.
