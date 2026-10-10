"""CareSentry Studio Skill

This skill enables Hermes to spawn and manage CareSentry-AI audit and visualization tools.

Tools:
- caresentry_studio.audit: Run deterministic clinical safety audit
- caresentry_studio.normalize_drugs: Normalize drug names against clinical rules
- caresentry_studio.omission_check: Check for missing clinical constraints
- caresentry_studio.render_heatmap: Generate attention heatmap HTML
- caresentry_studio.verify_log: Verify hash-chained audit log integrity
"""

name: caresentry-studio
version: 1.0.0
license: Apache-2.0
author: CareSentry Studio Lane
url: https://github.com/your-org/caresentry-ai

# Description
CareSentry-AI is a deterministic attention-anchored clinical verification harness for open-weight language models. This skill provides tools for:
- Running the clinical safety invariant linter offline
- Normalizing drug names against the clinical rules matrix
- Checking for omitted critical constraints (omission detection)
- Rendering attention heatmaps from trace data
- Verifying hash-chained audit logs for integrity

# Usage
Load this skill to enable the following commands:

## Audit Tool
```bash
hermes caresentry_studio.audit --records "Patient has severe allergy to penicillin" --summary "Discharge on Amoxicillin 500mg"
```

## Heatmap Tool
```bash
hermes caresentry_studio.render_heatmap --trace-file trace.json --output heatmap.html
```

## Log Verification
```bash
hermes caresentry_studio.verify_log --log-path studio/audit/audit_log.jsonl
```

# Dependencies
Requires: Python 3.10+, torch, transformers, bitsandbytes (for NF4), gradio (for web UI)

# Installation
```bash
pip install -e .
```

# MCP Configuration
To use this skill as an MCP server, run:
```bash
python -m caresentry_studio.mcp_server.server
```

Configure in `config.yaml`:
```yaml
mcp:
  stdio:
    - name: caresentry-studio
      command: python -m caresentry_studio.mcp_server.server
      args: []
```

# License
Apache-2.0
---
"""