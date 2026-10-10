"""Tests that verify no external CDN or network URLs exist in guard/ui (U-01, Section 7)."""

import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui"


def test_no_external_urls_in_ui_assets():
    """Ensure zero external http(s):// URLs exist in UI assets, only 127.0.0.1 or relative paths."""
    url_pattern = re.compile(r"https?://([^\s\"\'<>]+)")
    violations = []

    for file_path in UI_DIR.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".html", ".js", ".css", ".json", ".svg"]:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            matches = url_pattern.findall(text)
            for host_match in matches:
                # Strip path / port
                host = host_match.split("/")[0].split(":")[0]
                # Allow strictly 127.0.0.1 and localhost or xml namespaces
                if host not in ["127.0.0.1", "localhost", "www.w3.org"]:
                    violations.append(f"{file_path.name}: forbidden external URL host '{host}' ({host_match})")

    assert not violations, f"External URLs found in guard/ui/:\n" + "\n".join(violations)
