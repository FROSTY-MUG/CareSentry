"""GPU lock file manager for CareSentry-AI.

Provides a file-based lock so only one process/agent can run GPU-bound model
operations at a time.  Used by all lanes before loading a model onto the GPU.

Usage:
    # Context manager (recommended)
    with gpu_lock("guard"):
        run_model(...)

    # Manual acquire / release
    lock = GPULock(owner="studio")
    lock.acquire()
    try:
        run_model(...)
    finally:
        lock.release()

    # CLI
    python -m ops.tools.gpu_lock acquire --owner studio
    python -m ops.tools.gpu_lock status
    python -m ops.tools.gpu_lock release
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

# Default lock directory – lives at repo root so all lanes share it
_DEFAULT_LOCK_DIR = Path(__file__).resolve().parents.joinpath("..", "..", ".locks")

LOCK_FILE_NAME = "gpu.lock"


@dataclass
class LockState:
    owner: str
    acquired_at: str  # ISO timestamp
    timeout_seconds: int
    pid: int
    host: str

    @property
    def expired(self) -> bool:
        acquired = datetime.datetime.fromisoformat(self.acquired_at)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - acquired).total_seconds() > self.timeout_seconds

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LockState":
        return cls(**d)


class GPULock:
    """File-based GPU lock."""

    def __init__(
        self,
        owner: str,
        lock_dir: Optional[Path] = None,
        timeout_seconds: int = 7200,  # 2 hours default
    ):
        self.owner = owner
        self.lock_dir = Path(lock_dir) if lock_dir else _DEFAULT_LOCK_DIR
        self.lock_file = self.lock_dir / LOCK_FILE_NAME
        self.timeout_seconds = timeout_seconds

    # -- public API ---------------------------------------------------------

    def acquire(self, blocking: bool = True, poll_interval: float = 1.0) -> bool:
        """Acquire the GPU lock.

        Returns True on success.  If blocking=False, returns False immediately
        when the lock is held.  If blocking=True, waits until the lock is free
        or the existing lock expires.
        """
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                state = self._read_lock()
            except FileNotFoundError:
                state = None

            if state is None or state.expired:
                # Try to claim it
                claimed = self._write_lock()
                if claimed:
                    return True
                # Another process beat us – retry or bail
                if not blocking:
                    return False
                time.sleep(poll_interval)
                continue

            # Lock is held by someone else and not expired
            if not blocking:
                return False
            remaining = self._remaining_seconds(state)
            if remaining <= 0:
                continue  # expired, retry claim
            time.sleep(min(poll_interval, remaining))

    def release(self) -> bool:
        """Release the GPU lock if we own it."""
        try:
            state = self._read_lock()
        except FileNotFoundError:
            return False
        if state.owner == self.owner:
            self.lock_file.unlink(missing_ok=True)
            return True
        return False

    @contextmanager
    def __call__(self):
        """Context manager: ``with gpu_lock('guard'): ...``"""
        self.acquire()
        try:
            yield self
        finally:
            self.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

    def status(self) -> Optional[LockState]:
        """Return current lock state or None if no lock file."""
        try:
            return self._read_lock()
        except FileNotFoundError:
            return None

    # -- internal -----------------------------------------------------------

    def _read_lock(self) -> LockState:
        data = json.loads(self.lock_file.read_text(encoding="utf-8"))
        return LockState.from_dict(data)

    def _write_lock(self) -> bool:
        """Atomically attempt to write the lock. Returns True on success."""
        try:
            state = LockState(
                owner=self.owner,
                acquired_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                timeout_seconds=self.timeout_seconds,
                pid=os.getpid(),
                host=os.uname().nodename,
            )
            tmp = self.lock_file.with_suffix(".lock.tmp")
            tmp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
            tmp.rename(self.lock_file)
            return True
        except (OSError, json.JSONDecodeError):
            return False

    @staticmethod
    def _remaining_seconds(state: LockState) -> float:
        acquired = datetime.datetime.fromisoformat(state.acquired_at)
        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed = (now - acquired).total_seconds()
        return max(0, state.timeout_seconds - elapsed)


def gpu_lock(
    owner: str,
    lock_dir: Optional[Path] = None,
    timeout_seconds: int = 7200,
) -> GPULock:
    """Convenience constructor used by other lanes."""
    return GPULock(owner=owner, lock_dir=lock_dir, timeout_seconds=timeout_seconds)


# -- CLI --------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="CareSentry GPU lock manager")
    sub = parser.add_subparsers(dest="command")

    acq = sub.add_parser("acquire", help="Acquire the GPU lock")
    acq.add_argument("--owner", required=True, help="Lane or component name")
    acq.add_argument("--timeout", type=int, default=7200, help="Timeout in seconds")
    acq.add_argument("--non-blocking", action="store_true", help="Fail immediately if locked")

    sub.add_parser("release", help="Release the GPU lock")
    st = sub.add_parser("status", help="Show current lock status")

    args = parser.parse_args()

    lock = GPULock(owner=args.owner if hasattr(args, "owner") else "", timeout_seconds=getattr(args, "timeout", 7200))

    if args.command == "acquire":
        ok = lock.acquire(blocking=not args.non_blocking)
        if ok:
            print(f"GPU lock acquired by '{args.owner}' (pid {os.getpid()})")
            return 0
        else:
            st = lock.status()
            if st:
                print(f"GPU lock held by '{st.owner}' (pid {st.pid}, acquired {st.acquired_at})")
            else:
                print("GPU lock is free but could not claim it (race)")
            return 1

    elif args.command == "release":
        ok = lock.release()
        if ok:
            print("GPU lock released")
            return 0
        else:
            st = lock.status()
            if st:
                print(f"Lock held by '{st.owner}', not released (you must be the owner)")
            else:
                print("No lock found")
            return 1

    elif args.command == "status":
        st = lock.status()
        if st:
            remaining = GPULock._remaining_seconds(st)
            print(f"Held by: {st.owner} (pid {st.pid})")
            print(f"Acquired: {st.acquired_at}")
            print(f"Timeout:  {st.timeout_seconds}s (remaining: {remaining:.0f}s)")
            print(f"Expired:  {st.expired}")
        else:
            print("GPU lock is free")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
