"""Hash-Chained Audit Log (F-13)

Records audit entries with SHA-256 hash chains.
Prevents log tampering by storing hashes of entries rather than raw sensitive text.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List

class HashChainedAuditLog:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = "0" * 64
        self._init_chain()

    def _init_chain(self):
        """Read last hash from log file if it exists."""
        if self.log_path.exists():
            lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                last_line = json.loads(lines[-1])
                self.last_hash = last_line.get("entry_hash", "0" * 64)

    def log_event(self, event_type: str, details: Dict[str, Any]) -> str:
        """Append an audit entry to the hash-chained log."""
        timestamp = time.time()
        
        # Hash event details to preserve privacy
        details_str = json.dumps(details, sort_keys=True)
        details_hash = hashlib.sha256(details_str.encode("utf-8")).hexdigest()

        # Build payload
        payload = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details_hash": details_hash,
            "prev_hash": self.last_hash,
        }

        # Calculate entry hash
        payload_str = json.dumps(payload, sort_keys=True)
        entry_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        payload["entry_hash"] = entry_hash

        # Write line
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        self.last_hash = entry_hash
        return entry_hash

    def verify_integrity(self) -> bool:
        """Verify the integrity of the entire hash chain."""
        if not self.log_path.exists():
            return True

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        expected_prev = "0" * 64

        for idx, line in enumerate(lines):
            entry = json.loads(line)
            actual_prev = entry.get("prev_hash")
            if actual_prev != expected_prev:
                print(f"Tamper detected at line {idx+1}: prev_hash mismatch")
                return False

            # Verify current entry hash
            entry_copy = entry.copy()
            actual_entry_hash = entry_copy.pop("entry_hash", "")
            payload_str = json.dumps(entry_copy, sort_keys=True)
            calc_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            if calc_hash != actual_entry_hash:
                print(f"Tamper detected at line {idx+1}: entry_hash mismatch")
                return False

            expected_prev = actual_entry_hash

        return True

def main():
    log_file = Path("studio/audit/audit_log.jsonl")
    audit = HashChainedAuditLog(log_file)
    
    # Log sample events
    h1 = audit.log_event("AUDIT_PASS", {"case": "001", "rules_checked": 5})
    h2 = audit.log_event("AUDIT_FAIL", {"case": "002", "violations": ["ALLERGY"]})

    print(f"Logged 2 events. Latest hash: {h2[:16]}...")
    print(f"Integrity check: {'PASSED' if audit.verify_integrity() else 'FAILED'}")

if __name__ == "__main__":
    main()
