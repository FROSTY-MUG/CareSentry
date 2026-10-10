name: caresentry-studio
skill: caresentry-studio
version: 1.0.0
license: Apache-2.0
author: CareSentry Studio Lane
url: https://github.com/your-org/caresentry-ai

# MCP Client Configuration
# This file is for the MCP client to automatically discover the caresentry-studio skill

# Tools provided by this skill (via MCP server)
# - audit: Run deterministic clinical safety audit on EHR and summary
# - normalize_drugs: Normalize drug names against clinical rules matrix
# - omission_check: Check for missing clinical constraints
# - render_heatmap: Generate HTML attention heatmap from trace data
# - verify_log: Verify hash-chained audit log integrity

# Usage examples:
# hermes caresentry_studio.audit --records "..." --summary "..."
# hermes caresentry_studio.render_heatmap --trace-file trace.json --output heatmap.html
# hermes caresentry_studio.verify_log --log-path studio/audit/audit_log.jsonl

# Installation
pip install -e .

# MCP Server Setup
Run the MCP server with:
python -m caresentry_studio.mcp_server.server

# Add to config.yaml:
mcp:
  stdio:
    - name: caresentry-studio
      command: python -m caresentry_studio.mcp_server.server
      args: []
