"""Unit tests for Track B Ownership Guard."""

import os
import subprocess
import sys
from pathlib import Path
import pytest

from plus.tools.check_ownership import check_ownership, TRACK_B_PREFIXES


def test_ownership_prefixes_cover_track_b_paths():
    """Verify that Track B prefixes allowlist covers all plus assets."""
    assert any("plus/" in p.replace("\\", "/") for p in TRACK_B_PREFIXES)
    assert any(".agents/skills/caresentry-plus/" in p.replace("\\", "/") for p in TRACK_B_PREFIXES)
    assert any(".github/workflows/plus-" in p.replace("\\", "/") for p in TRACK_B_PREFIXES)
    assert any("contracts/requests/B-" in p.replace("\\", "/") for p in TRACK_B_PREFIXES)


def test_ownership_guard_passes_on_current_tree():
    """Current repository tree must pass ownership check with return code 0."""
    res = check_ownership()
    assert res == 0, "Ownership guard failed on current working tree!"
