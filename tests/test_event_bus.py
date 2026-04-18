"""Event bus: peek/commit semantics + INC-007 max-merge invariant.

Per Kai's spec-test-suite.md: tests assert real invariants, not
just smoke-pass. Each test would FAIL if the underlying contract
broke (silent at-most-once delivery, regressing offsets, etc.).
"""

from __future__ import annotations

import json
import os
import unittest

from tests import _fixtures


def _send(root: str, channel: str, sender: str, body: str) -> None:
    """Send a message through scripts/bus/send.py."""
    result = _fixtures.run_script(
        "scripts/bus/send.py",
        "--channel", channel,
        "--from", sender,
        "--body", body,
        "--bus", os.path.join(root, "system", "bus"),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"send.py failed: {result.stderr}"
        )


def _peek(root: str, agent: str, offsets_path: str) -> str:
    """Peek bus messages without committing."""
    return _fixtures.run_script(
        "scripts/bus/read.py",
        "--agent", agent,
        "--bus", os.path.join(root, "system", "bus"),
        "--offsets", offsets_path,
        "--peek",
    ).stdout


def _commit(root: str, agent: str, offsets_path: str) -> None:
    """Commit (advance offsets) bus messages."""
    _fixtures.run_script(
        "scripts/bus/read.py",
        "--agent", agent,
        "--bus", os.path.join(root, "system", "bus"),
        "--offsets", offsets_path,
        "--update",
    )


class EventBusPeekCommitTest(unittest.TestCase):
    """At-least-once delivery: peek shows N, commit, peek shows 0."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        _fixtures.mk_channel(self.root, "standup")
        self.offsets = os.path.join(
            self.root, "workspaces", "bob", "bus-offsets.json"
        )
        os.makedirs(
            os.path.dirname(self.offsets), exist_ok=True
        )

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_peek_then_commit_roundtrip(self) -> None:
        for i in range(3):
            _send(self.root, "standup", "alice", f"msg-{i}")

        # Peek: bob should see all 3 messages
        peeked = _peek(self.root, "bob", self.offsets)
        for i in range(3):
            self.assertIn(f"msg-{i}", peeked)
        self.assertIn("Peeked 3 message(s)", peeked)

        # Crash simulation: re-peeking BEFORE commit must show
        # the same 3 messages (at-least-once delivery)
        peeked_again = _peek(self.root, "bob", self.offsets)
        for i in range(3):
            self.assertIn(f"msg-{i}", peeked_again)

        # Commit: advance offsets
        _commit(self.root, "bob", self.offsets)

        # Peek after commit: should see 0
        after = _peek(self.root, "bob", self.offsets)
        self.assertIn("No new messages", after)
        for i in range(3):
            self.assertNotIn(f"msg-{i}", after)


class EventBusOffsetMergeTest(unittest.TestCase):
    """INC-007: stale writers must not regress another reader's offset."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        _fixtures.mk_channel(self.root, "standup")
        self.offsets = os.path.join(
            self.root, "workspaces", "carol", "bus-offsets.json"
        )
        os.makedirs(
            os.path.dirname(self.offsets), exist_ok=True
        )

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_offset_max_merge_never_regresses(self) -> None:
        # Send 5 messages, commit them — establishes a high
        # legitimate offset in the file.
        for i in range(5):
            _send(self.root, "standup", "alice", f"msg-{i}")
        _commit(self.root, "carol", self.offsets)
        with open(self.offsets) as f:
            high_state = json.load(f)
        high_offsets = (
            high_state.get("offsets", {})
            .get("standup", {})
        )
        self.assertTrue(
            high_offsets, "first commit didn't write offsets"
        )
        max_high = max(high_offsets.values())
        self.assertGreater(
            max_high, 0,
            "expected non-zero offset after committing 5 msgs",
        )

        # INC-007: a stale writer (holding a lower in-memory
        # snapshot) must not be able to regress the on-disk
        # offset below max_high. Import the save helper via
        # importlib (scripts/ isn't a package — by design, the
        # framework ships scripts as standalone executables).
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_bus_read",
            os.path.join(
                _fixtures.REPO, "scripts", "bus", "read.py"
            ),
        )
        bus_read = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bus_read)
        save_offsets_locked = bus_read.save_offsets_locked

        stale = {
            wk: max(0, val - 3)
            for wk, val in high_offsets.items()
        }
        merged = save_offsets_locked(
            self.offsets, {"standup": stale}
        )

        for wk, original_val in high_offsets.items():
            self.assertGreaterEqual(
                merged["standup"][wk], original_val,
                f"INC-007 regression: week {wk} dropped from "
                f"{original_val} to {merged['standup'][wk]}",
            )

        # Re-read from disk to verify the on-disk file matches
        # (not just the in-memory return value).
        with open(self.offsets) as f:
            on_disk = json.load(f)
        for wk, original_val in high_offsets.items():
            self.assertGreaterEqual(
                on_disk["offsets"]["standup"][wk],
                original_val,
                f"on-disk regressed at week {wk}",
            )


if __name__ == "__main__":
    unittest.main()
