"""Tests for ops/tools/gpu_lock.py"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ops.tools.gpu_lock import GPULock, LockState


def test_acquire_release():
    lock = GPULock(owner="lane-a", timeout_seconds=60)
    assert lock.acquire(blocking=False) is True
    assert lock.release() is True
    assert lock.status() is None


def test_context_manager():
    lock = GPULock(owner="ctx-lane", timeout_seconds=60)
    with lock:
        assert lock.status() is not None
    assert lock.status() is None


def test_lock_state_expired():
    state = LockState(
        owner="x",
        acquired_at=(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=3600)).isoformat(),
        timeout_seconds=60,
        pid=1,
        host="h",
    )
    assert state.expired is True
