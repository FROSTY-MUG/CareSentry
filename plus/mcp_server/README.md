# CareSentry-AI Plus MCP Server (F-12)

Stdio Model Context Protocol (MCP) server providing zero-dependency deterministic clinical invariant auditing, drug entity normalization, reverse omission checking, and attention heatmap generation.

## Supported MCP Tools

- `audit_plus(records: str, summary: str)`: Executes end-to-end Track A + Track B clinical audit and emits `plus_audit_result.v1`.
- `normalize_drugs(text: str)`: Resolves brand names, generics, and clinical acronyms to canonical RxNorm/ATC entities.
- `omission_check(records: str, summary: str)`: Reverse safety gate identifying documented EHR constraints omitted in discharge summaries.
- `render_heatmap(records: str, needle: str, trace_path: str)`: Generates interactive self-contained HTML token attention heatmaps.

## Client Configuration Examples

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "caresentry-plus": {
      "command": "python",
      "args": ["-m", "caresentry_plus.mcp"],
      "cwd": "/path/to/caresentry-ai"
    }
  }
}
```

### Antigravity / Cursor MCP Config
```json
{
  "mcp": {
    "servers": {
      "caresentry_plus": {
        "command": "python",
        "args": ["plus/mcp_server/server.py"]
      }
    }
  }
}
```
