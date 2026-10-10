"""Tests for src/caresentry_studio/webui/app.py"""

import sys
from pathlib import Path
import pytest

# Ensure caresentry_studio is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from caresentry_studio.webui.app import create_ui

def test_webui_creates_interface():
    ui = create_ui()
    assert ui is not None
    # Verify UI has expected components
    assert hasattr(ui, "components")
    # Check for audit functionality
    found_audit = False
    for comp in ui.components:
        if hasattr(comp, "elem") and "audit" in str(comp.elem).lower():
            found_audit = True
    assert found_audit, "UI missing audit functionality"
