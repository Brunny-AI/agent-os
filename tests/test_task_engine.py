"""Task engine: finish-to-start invariant + lease expiry.

Per Kai's spec-test-suite.md: 2 tests covering the engine's
core contract — that completion REQUIRES a next claim with an
artifact, and that stale leases get reclaimed.
"""

from __future__ import annotations

import datetime
import json
import os
import unittest

from tests import _fixtures


def _engine(
    root: str, agent: str, *args: str
) -> "subprocess.CompletedProcess":  # noqa: F821
    """Invoke task engine with AGENT_OS_ROOT pointing at root."""
    return _fixtures.run_script(
        "scripts/task/engine.py",
        "--agent", agent, *args,
        env_extra={"AGENT_OS_ROOT": root},
    )


def _state_path(root: str, agent: str) -> str:
    return os.path.join(
        root, "workspaces", agent,
        "logs", "progress", "task-engine-state.json",
    )


class TaskEngineLifecycleTest(unittest.TestCase):
    """READY → CLAIMED → IN_PROGRESS → COMPLETE happy path
    plus the finish-to-start invariant: completing T1 requires
    T2 already claimed AND T2 has an artifact."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_claim_and_complete_happy_path(self) -> None:
        # Claim T-1, produce artifact (state: IN_PROGRESS)
        r = _engine(
            self.root, "alice",
            "--claim", "T-1",
            "--claim-desc", "first task",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CLAIMED: T-1", r.stdout)

        r = _engine(
            self.root, "alice",
            "--artifact", "T-1", "out/first.py",
        )
        self.assertIn("IN_PROGRESS: T-1", r.stdout)

        # Complete T-1 WITHOUT a follow-up claim → must fail
        # (finish-to-start invariant)
        r = _engine(self.root, "alice", "--complete", "T-1")
        self.assertNotEqual(
            r.returncode, 0,
            "complete without next-claim should fail "
            "(finish-to-start invariant)",
        )
        self.assertIn("BLOCKED", r.stderr)

        # Claim T-2 + artifact, THEN complete T-1
        _engine(
            self.root, "alice",
            "--claim", "T-2",
            "--claim-desc", "second task",
        )
        _engine(
            self.root, "alice",
            "--artifact", "T-2", "out/second.py",
        )
        r = _engine(self.root, "alice", "--complete", "T-1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("COMPLETE: T-1", r.stdout)

        # Verify state on disk
        with open(_state_path(self.root, "alice")) as f:
            state = json.load(f)
        self.assertEqual(
            state["tasks"]["T-1"]["status"], "COMPLETE"
        )
        self.assertEqual(
            state["tasks"]["T-2"]["status"], "IN_PROGRESS"
        )


class TaskEngineLeaseExpiryTest(unittest.TestCase):
    """LEASE_MINUTES (15) elapses → --check-lease marks EXPIRED."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_lease_expires_after_15min(self) -> None:
        # Claim a task (lease set to now+15min)
        r = _engine(
            self.root, "bob",
            "--claim", "T-LEASE",
            "--claim-desc", "lease test",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        path = _state_path(self.root, "bob")
        with open(path) as f:
            state = json.load(f)

        # Backdate lease_expires by 1 minute (now - 60s).
        # The engine reads wall-clock; we don't mock time —
        # we mutate the lease so the existing wall-clock check
        # naturally evaluates as expired.
        past = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)
        ).isoformat()
        state["tasks"]["T-LEASE"]["lease_expires"] = past

        with open(path, "w") as f:
            json.dump(state, f)

        # check-lease should detect expiry, mark EXPIRED, and
        # exit non-zero so the poll knows to take action.
        r = _engine(self.root, "bob", "--check-lease")
        self.assertNotEqual(
            r.returncode, 0,
            "check-lease must exit non-zero on expiry "
            "so the poll prompt acts",
        )
        self.assertIn("LEASE EXPIRED", r.stdout)
        self.assertIn("T-LEASE", r.stdout)

        # State should now reflect EXPIRED
        with open(path) as f:
            state = json.load(f)
        self.assertEqual(
            state["tasks"]["T-LEASE"]["status"], "EXPIRED"
        )

        # A subsequent claim of the SAME task must succeed
        # (EXPIRED is not CLAIMED/IN_PROGRESS, so the duplicate
        # guard doesn't trip).
        r = _engine(
            self.root, "bob",
            "--claim", "T-LEASE",
            "--claim-desc", "re-claim after expiry",
        )
        self.assertEqual(
            r.returncode, 0,
            f"re-claim of expired task should succeed: "
            f"{r.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
