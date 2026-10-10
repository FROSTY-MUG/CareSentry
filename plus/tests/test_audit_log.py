"""Unit tests for F-13 Hash-Chained Audit Log."""

import json
from pathlib import Path
import pytest

from caresentry_plus.audit.audit_log import AuditLogger, GENESIS_PREV_HASH


def test_audit_log_append_and_chaining(tmp_path):
    """Test cryptographic append-only chaining."""
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    # 1. Entry 0 (Genesis)
    e0 = logger.log_audit(
        raw_ehr="Patient record text A",
        summary="Summary text A",
        rule_packs=["pack_1"],
        model_id="test-model",
        verdict="PASS",
        violations_count=0,
        omissions_count=0,
    )
    assert e0.entry_index == 0
    assert e0.prev_hash == GENESIS_PREV_HASH
    assert len(e0.entry_hash) == 64

    # 2. Entry 1
    e1 = logger.log_audit(
        raw_ehr="Patient record text B",
        summary="Summary text B",
        rule_packs=["pack_1", "pack_2"],
        model_id="test-model",
        verdict="FAIL",
        violations_count=1,
        omissions_count=1,
    )
    assert e1.entry_index == 1
    assert e1.prev_hash == e0.entry_hash
    assert len(e1.entry_hash) == 64

    # 3. Privacy requirement: verify no raw text stored in log file
    log_content = log_file.read_text(encoding="utf-8")
    assert "Patient record text A" not in log_content
    assert "Summary text B" not in log_content

    # 4. Verification passes on intact log
    is_valid, errors = AuditLogger.verify_log(log_file)
    assert is_valid is True
    assert len(errors) == 0


def test_audit_log_tamper_detection(tmp_path):
    """F-13 Requirement: verify-log detects any tampering."""
    log_file = tmp_path / "tampered_audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    logger.log_audit("EHR 1", "Summary 1", ["pack_1"], "model", "PASS", 0, 0)
    logger.log_audit("EHR 2", "Summary 2", ["pack_1"], "model", "FAIL", 2, 1)
    logger.log_audit("EHR 3", "Summary 3", ["pack_1"], "model", "PASS", 0, 0)

    # Tamper with entry 1: change verdict from FAIL to PASS
    lines = log_file.read_text(encoding="utf-8").splitlines()
    entry1 = json.loads(lines[1])
    entry1["verdict"] = "PASS"  # Tampered!
    lines[1] = json.dumps(entry1)
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Verification must fail and detect tampering
    is_valid, errors = AuditLogger.verify_log(log_file)
    assert is_valid is False
    assert len(errors) >= 1
    assert any("tampering" in err.lower() or "hash chain break" in err.lower() for err in errors)
