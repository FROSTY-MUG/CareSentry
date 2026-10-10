"""Tests for K-07 Extensible Plugin Framework & Monotonic Safety."""

import pytest
from harness.plugins import (
    MonotonicSafetyViolation,
    PluginManager,
    PluginMetadata,
    get_plugin_manager,
)


@pytest.fixture(autouse=True)
def clean_plugin_manager():
    mgr = get_plugin_manager()
    mgr.reset()
    yield mgr
    mgr.reset()


def test_plugin_registration(clean_plugin_manager):
    mgr = clean_plugin_manager
    meta = PluginMetadata(
        name="pediatric_guard",
        version="1.0.0",
        author="Pediatrics Lab",
        description="Pediatric dosing guard",
    )
    mgr.register_plugin(meta)
    assert "pediatric_guard" in mgr._plugins


def test_monotonic_safety_allows_adding_violations(clean_plugin_manager):
    mgr = clean_plugin_manager

    # Hook that adds an extra violation
    def strict_hook(result):
        res = dict(result)
        v = list(res.get("violations", []))
        v.append({"rule_id": "CS-PED-001", "rule_name": "Weight based check"})
        res["violations"] = v
        res["status"] = "FAIL"
        return res

    mgr.register_post_lint_hook(strict_hook)

    initial = {"status": "PASS", "violations": []}
    out = mgr.apply_post_lint_hooks(initial)
    assert out["status"] == "FAIL"
    assert len(out["violations"]) == 1


def test_monotonic_safety_rejects_fail_to_pass_override(clean_plugin_manager):
    mgr = clean_plugin_manager

    # Rogue hook attempting to suppress safety failure
    def rogue_hook(result):
        res = dict(result)
        res["status"] = "PASS"
        res["violations"] = []
        return res

    mgr.register_post_lint_hook(rogue_hook)

    initial = {
        "status": "FAIL",
        "violations": [{"rule_id": "CS-ALG-001", "rule_name": "Penicillin allergy conflict"}],
    }

    with pytest.raises(MonotonicSafetyViolation, match="override FAIL status to PASS"):
        mgr.apply_post_lint_hooks(initial)


def test_monotonic_safety_rejects_suppressing_existing_violation(clean_plugin_manager):
    mgr = clean_plugin_manager

    # Rogue hook that keeps status FAIL but removes a violation
    def suppress_violation_hook(result):
        res = dict(result)
        res["violations"] = [{"rule_id": "CS-OTHER-001", "rule_name": "Other"}]
        return res

    mgr.register_post_lint_hook(suppress_violation_hook)

    initial = {
        "status": "FAIL",
        "violations": [{"rule_id": "CS-ALG-001", "rule_name": "Penicillin allergy conflict"}],
    }

    with pytest.raises(MonotonicSafetyViolation, match="suppressed existing invariant violations"):
        mgr.apply_post_lint_hooks(initial)
