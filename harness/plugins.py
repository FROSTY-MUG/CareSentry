"""CareSentry-AI Extensible Plugin Framework with Monotonic Safety Enforcement.

Implements K-07:
- Extension entry points:
  1. rule_packs: Custom clinical rule packs (e.g. hepatic, pediatric, ICU)
  2. mitigations: Custom prompt remediation strategies
  3. audit_hooks: Telemetry, observability, and lifecycle audit hooks
- Monotonic Safety Principle (Release Gate & Critical Safety Guarantee):
  No plugin can ever override a FAIL into a PASS or suppress detected invariant violations.
  A plugin can only ADD detected violations or preserve existing violations.
  Any attempt to downgrade a FAIL or delete detected violations immediately raises
  MonotonicSafetyViolation and aborts execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("caresentry.plugins")


class MonotonicSafetyViolation(PermissionError):
    """Raised when an external plugin attempts to suppress violations or turn FAIL into PASS."""
    pass


class PluginRegistrationError(ValueError):
    """Raised when an invalid plugin or duplicate non-overridable hook is registered."""
    pass


@dataclass
class PluginMetadata:
    """Metadata for a registered CareSentry plugin."""
    name: str
    version: str
    author: str = ""
    description: str = ""
    enabled: bool = True


class PluginManager:
    """Central registry and lifecycle dispatcher for CareSentry plugins."""

    _instance: Optional[PluginManager] = None

    def __init__(self):
        self._plugins: Dict[str, PluginMetadata] = {}
        self._rule_packs: Dict[str, Dict[str, Any]] = {}
        self._audit_hooks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._post_lint_filters: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    @classmethod
    def get_instance(cls) -> PluginManager:
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance

    def register_plugin(self, metadata: PluginMetadata) -> None:
        """Register a new plugin package."""
        if metadata.name in self._plugins:
            logger.info(f"Updating plugin registration: {metadata.name} v{metadata.version}")
        self._plugins[metadata.name] = metadata
        logger.info(f"Registered plugin: {metadata.name} v{metadata.version}")

    def register_rule_pack(self, pack_id: str, rules_data: Dict[str, Any]) -> None:
        """Register an additional clinical rule pack."""
        from harness.clinical_linter import validate_rules_schema

        # Validate schema before accepting
        validate_rules_schema(rules_data)
        self._rule_packs[pack_id] = rules_data
        logger.info(f"Registered clinical rule pack: {pack_id} with {len(rules_data.get('rules', []))} rules")

    def register_audit_hook(self, hook: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register an audit/telemetry hook invoked during lifecycle events."""
        self._audit_hooks.append(hook)

    def register_post_lint_hook(self, hook: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Register a post-lint hook with monotonic safety enforcement."""
        self._post_lint_filters.append(hook)

    def get_all_rule_packs(self) -> Dict[str, Dict[str, Any]]:
        """Return all registered rule packs."""
        return dict(self._rule_packs)

    def trigger_audit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Dispatch audit event to registered hooks."""
        for hook in self._audit_hooks:
            try:
                hook(event_name, payload)
            except Exception as e:
                logger.warning(f"Audit hook error on event '{event_name}': {e}")

    def apply_post_lint_hooks(self, lint_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply post-lint hooks while enforcing strict monotonic safety.

        Rules:
        - If lint_result is FAIL, no hook may change status to PASS.
        - No hook may remove pre-existing violations.
        - Hooks may add additional violations (narrowing safety) but never remove them.
        """
        current_status = lint_result.get("status", "PASS")
        current_violations = list(lint_result.get("violations", []))
        initial_violation_ids: Set[str] = {
            v.get("rule_id", "") for v in current_violations if isinstance(v, dict)
        }

        modified_result = dict(lint_result)

        for hook in self._post_lint_filters:
            new_result = hook(dict(modified_result))
            new_status = new_result.get("status", "PASS")
            new_violations = new_result.get("violations", [])
            new_violation_ids: Set[str] = {
                v.get("rule_id", "") for v in new_violations if isinstance(v, dict)
            }

            # MONOTONIC SAFETY ENFORCEMENT
            if current_status == "FAIL" and new_status == "PASS":
                raise MonotonicSafetyViolation(
                    "Monotonic Safety Violation: Plugin attempted to override FAIL status to PASS. "
                    "Clinical safety invariants cannot be cleared by external plugins."
                )

            # Check if any original violations were suppressed
            missing_violations = initial_violation_ids - new_violation_ids
            if missing_violations:
                raise MonotonicSafetyViolation(
                    f"Monotonic Safety Violation: Plugin suppressed existing invariant violations: {missing_violations}. "
                    "Plugins may only introduce additional clinical constraints, never suppress detected violations."
                )

            modified_result = new_result

        return modified_result

    def reset(self) -> None:
        """Reset all registered plugins and hooks (used for isolated testing)."""
        self._plugins.clear()
        self._rule_packs.clear()
        self._audit_hooks.clear()
        self._post_lint_filters.clear()


# Convenience global functions
def get_plugin_manager() -> PluginManager:
    return PluginManager.get_instance()


def register_audit_hook(hook: Callable[[str, Dict[str, Any]], None]) -> None:
    PluginManager.get_instance().register_audit_hook(hook)


def register_rule_pack(pack_id: str, rules_data: Dict[str, Any]) -> None:
    PluginManager.get_instance().register_rule_pack(pack_id, rules_data)
