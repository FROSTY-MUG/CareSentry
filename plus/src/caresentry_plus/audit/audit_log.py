"""Cryptographically Hash-Chained Audit Log.

Maintains an immutable, append-only JSONL log where each entry cryptographically
commits to its predecessors using SHA-256. Protects patient privacy by logging
cryptographic digests rather than raw PHI or clinical narratives (NFR-B6).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GENESIS_PREV_HASH = "0" * 64


@dataclass
class AuditLogEntry:
    entry_index: int
    timestamp: str
    input_hash: str
    rule_packs: List[str]
    model_id: str
    verdict: str
    violations_count: int
    omissions_count: int
    retry_count: int
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """Manages append-only hash-chained audit logging and verification."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Compute SHA-256 digest of arbitrary text."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_block_hash(entry_dict: Dict[str, Any]) -> str:
        """Compute deterministic hash of an entry excluding entry_hash itself."""
        payload = {k: v for k, v in entry_dict.items() if k != "entry_hash"}
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def get_last_entry(self) -> Optional[AuditLogEntry]:
        """Read last entry from the log file if it exists."""
        if not self.log_path or not self.log_path.exists():
            return None

        last_line = None
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line

        if not last_line:
            return None

        data = json.loads(last_line)
        return AuditLogEntry(**data)

    def log_audit(
        self,
        raw_ehr: str,
        summary: str,
        rule_packs: List[str],
        model_id: str,
        verdict: str,
        violations_count: int,
        omissions_count: int,
        retry_count: int = 0,
    ) -> AuditLogEntry:
        """Append an audit transaction to the hash-chain log."""
        combined_input = f"{raw_ehr.strip()}|||{summary.strip()}"
        input_hash = self.compute_sha256(combined_input)

        last_entry = self.get_last_entry()
        if last_entry is None:
            new_index = 0
            prev_hash = GENESIS_PREV_HASH
        else:
            new_index = last_entry.entry_index + 1
            prev_hash = last_entry.entry_hash

        timestamp = datetime.now(timezone.utc).isoformat()

        entry_data = {
            "entry_index": new_index,
            "timestamp": timestamp,
            "input_hash": input_hash,
            "rule_packs": sorted(rule_packs),
            "model_id": model_id,
            "verdict": verdict,
            "violations_count": violations_count,
            "omissions_count": omissions_count,
            "retry_count": retry_count,
            "prev_hash": prev_hash,
        }

        entry_hash = self.compute_block_hash(entry_data)
        entry_data["entry_hash"] = entry_hash

        entry = AuditLogEntry(**entry_data)

        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

        return entry

    @classmethod
    def verify_log(cls, log_path: Path) -> Tuple[bool, List[str]]:
        """Verify the cryptographic integrity of an audit log.
        
        Detects tampering, truncated records, out-of-order blocks, or hash mismatches.
        """
        if not log_path.exists():
            return False, [f"Log file not found: {log_path}"]

        errors: List[str] = []
        expected_prev_hash = GENESIS_PREV_HASH
        expected_index = 0

        with open(log_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry_dict = json.loads(line)
                except Exception as e:
                    errors.append(f"Line {line_no}: Malformed JSON ({e})")
                    continue

                idx = entry_dict.get("entry_index")
                prev_hash = entry_dict.get("prev_hash")
                claimed_hash = entry_dict.get("entry_hash")

                if idx != expected_index:
                    errors.append(
                        f"Line {line_no}: Index discontinuity. Expected {expected_index}, got {idx}."
                    )

                if prev_hash != expected_prev_hash:
                    errors.append(
                        f"Line {line_no} (Index {idx}): Hash chain break. Expected prev_hash {expected_prev_hash[:12]}..., got {prev_hash[:12] if prev_hash else 'None'}."
                    )

                computed_hash = cls.compute_block_hash(entry_dict)
                if computed_hash != claimed_hash:
                    errors.append(
                        f"Line {line_no} (Index {idx}): Block tampering detected! Computed hash {computed_hash[:12]}... does not match claimed hash {claimed_hash[:12] if claimed_hash else 'None'}."
                    )

                expected_prev_hash = claimed_hash or ""
                expected_index += 1

        is_valid = (len(errors) == 0) and (expected_index > 0)
        return is_valid, errors
