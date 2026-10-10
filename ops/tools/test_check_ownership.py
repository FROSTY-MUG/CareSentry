"""Tests for ops/tools/check_ownership.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ops.tools.check_ownership import load_ownership, check_ownership


def test_load_ownership():
    data = load_ownership()
    assert "core" in data
    assert "studio" in data
    assert "clinical" in data
    assert "guard" in data
    assert "freebuff" in data


def test_check_ownership_violation():
    ownership = {
        "core": ["harness/", "tests/"],
        "studio": ["studio/", "eval/"],
    }
    files = ["studio/test.py", "harness/modified.py"]
    violations, warnings = check_ownership(files, ownership, "studio")
    assert any("harness/modified.py" in v for v in violations)


def test_check_ownership_ok():
    ownership = {
        "core": ["harness/", "tests/"],
        "studio": ["studio/", "eval/"],
    }
    files = ["studio/test.py", "eval/results/test.json"]
    violations, warnings = check_ownership(files, ownership, "studio")
    assert violations == []