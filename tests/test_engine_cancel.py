"""task-engine --cancel: graceful exit for stale tasks.

Cancellation is the missing third terminal state (beside
COMPLETE and EXPIRED). Without it, abandoned CLAIMED/BLOCKED
tasks accumulate and make the v4.6 parallel-work gate fire
spuriously forever.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import typing
import unittest


_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_ENGINE = os.path.join(_REPO, "scripts", "task", "engine.py")


def _run(
    agent: str, root: str, *args: str,
) -> subprocess.CompletedProcess[str]:
    """Invoke engine.py with AGENT_OS_ROOT pointing at root."""
    env = dict(os.environ)
    env["AGENT_OS_ROOT"] = root
    return subprocess.run(
        [sys.executable, _ENGINE, "--agent", agent, *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _state_path(root: str, agent: str) -> str:
    return os.path.join(
        root, "workspaces", agent,
        "logs", "progress", "task-engine-state.json",
    )


class CancelTerminalStateTest(unittest.TestCase):
    """Cancel transitions tasks to a terminal CANCELLED state
    from any active status, records when + why, and is
    idempotent-rejected on already-terminal tasks."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(
            shutil.rmtree, self.tmp, ignore_errors=True
        )
        self.agent = "alice"

    def _claim(self, tid: str) -> None:
        r = _run(
            self.agent, self.tmp, "--claim", tid,
            "--claim-desc", f"test task {tid}",
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr)

    def _read_state(self) -> dict[str, typing.Any]:
        with open(_state_path(self.tmp, self.agent)) as f:
            return json.load(f)

    def test_cancel_from_claimed(self) -> None:
        self._claim("T-1")
        r = _run(
            self.agent, self.tmp,
            "--cancel", "T-1",
            "--cancel-reason", "spec changed",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CANCELLED: T-1", r.stdout)
        self.assertIn("spec changed", r.stdout)

        task = self._read_state()["tasks"]["T-1"]
        self.assertEqual(task["status"], "CANCELLED")
        self.assertIsNotNone(task.get("cancelled_at"))
        self.assertEqual(
            task["cancelled_reason"], "spec changed"
        )

    def test_cancel_from_blocked(self) -> None:
        self._claim("T-2")
        _run(
            self.agent, self.tmp,
            "--block", "T-2",
            "--blocker-type", "dep", "--blocker-owner", "x",
        )
        r = _run(
            self.agent, self.tmp,
            "--cancel", "T-2",
            "--cancel-reason", "dep vanished",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        task = self._read_state()["tasks"]["T-2"]
        self.assertEqual(task["status"], "CANCELLED")
        # Original blocker metadata is preserved for audit
        self.assertEqual(task.get("blocker_type"), "dep")

    def test_cancel_without_next_claim_succeeds(self) -> None:
        # --complete requires next-claim+artifact. --cancel
        # MUST NOT — cancelling a stuck task shouldn't demand
        # a successor (the whole point is the task is going
        # nowhere).
        self._claim("T-ONLY")
        r = _run(
            self.agent, self.tmp,
            "--cancel", "T-ONLY",
            "--cancel-reason", "stuck",
        )
        self.assertEqual(
            r.returncode, 0,
            "cancel must not require follow-up claim "
            "(unlike --complete)",
        )

    def test_cancel_already_terminal_rejects(self) -> None:
        self._claim("T-X")
        _run(
            self.agent, self.tmp, "--cancel", "T-X",
            "--cancel-reason", "first",
        )
        # Second cancel on already-CANCELLED: must fail loud.
        r = _run(
            self.agent, self.tmp, "--cancel", "T-X",
            "--cancel-reason", "second",
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already", r.stderr)

    def test_cancel_unknown_task_rejects(self) -> None:
        r = _run(
            self.agent, self.tmp, "--cancel", "NOPE",
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stderr)

    def test_cancel_expired_rejects(self) -> None:
        # EXPIRED is set by the lease-expiry mechanism and
        # represents a real coast event in the audit trail.
        # --cancel must NOT overwrite it (would mask history).
        self._claim("T-EXP")
        # Force lease expiry: backdate lease in state file,
        # then run --check-lease so the engine flips status
        # → EXPIRED through its own code path (not a hand
        # edit pretending to be a lease).
        path = _state_path(self.tmp, self.agent)
        with open(path) as f:
            state = json.load(f)
        past = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)
        ).isoformat()
        state["tasks"]["T-EXP"]["lease_expires"] = past
        with open(path, "w") as f:
            json.dump(state, f)
        _run(self.agent, self.tmp, "--check-lease")

        # Now T-EXP is EXPIRED. --cancel must reject.
        r = _run(
            self.agent, self.tmp, "--cancel", "T-EXP",
            "--cancel-reason", "stale",
        )
        self.assertNotEqual(
            r.returncode, 0,
            "--cancel must not overwrite EXPIRED state",
        )
        self.assertIn("EXPIRED", r.stderr)

        # State unchanged: still EXPIRED, no cancelled_at.
        with open(path) as f:
            state = json.load(f)
        task = state["tasks"]["T-EXP"]
        self.assertEqual(task["status"], "EXPIRED")
        self.assertNotIn("cancelled_at", task)

    def test_cancelled_shows_under_status(self) -> None:
        self._claim("T-S")
        _run(
            self.agent, self.tmp, "--cancel", "T-S",
            "--cancel-reason", "why",
        )
        r = _run(self.agent, self.tmp, "--status")
        self.assertIn("CANCELLED", r.stdout)
        self.assertIn("T-S", r.stdout)


if __name__ == "__main__":
    unittest.main()
