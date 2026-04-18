"""Shift refresh: handoff sentinel gate + atomic flag write.

Per Kai's spec-test-suite.md (test_shift_manager equivalent):
the shift refresh shell script is the contract that says "agent
finished a 4h shift, sidecar may now terminate the session".
The non-trivial bits are the sentinel check (no half-written
handoff slips through) and the atomic flag write (sidecar never
sees a partial flag file).
"""

from __future__ import annotations

import os
import subprocess
import unittest

from tests import _fixtures


def _run_refresh(
    root: str, agent: str, reason: str
) -> subprocess.CompletedProcess:
    """Invoke shift_refresh.sh with AGENT_OS_ROOT pointing at root."""
    env = dict(os.environ)
    env["AGENT_OS_ROOT"] = root
    return subprocess.run(
        [
            "bash",
            os.path.join(
                _fixtures.REPO,
                "scripts", "cron", "shift_refresh.sh",
            ),
            agent, reason,
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class ShiftRefreshSentinelTest(unittest.TestCase):
    """Shift refresh refuses to fire without a complete handoff,
    fires atomically when the sentinel is present."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        self.agent = "alice"
        self.handoff = os.path.join(
            self.root, "workspaces", self.agent,
            "logs", "progress", "session-handoff.md",
        )
        self.flag = os.path.join(
            self.root, "system", f"shift-refresh-{self.agent}"
        )

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_4h_boundary_handoff_gate(self) -> None:
        # 1. No handoff file at all → must fail loud
        r = _run_refresh(self.root, self.agent, "4h boundary")
        self.assertNotEqual(
            r.returncode, 0,
            "missing handoff must block refresh",
        )
        self.assertIn("Handoff file not found", r.stderr)
        self.assertFalse(
            os.path.exists(self.flag),
            "no flag should exist after a blocked refresh",
        )

        # 2. Handoff exists but missing the sentinel → fail
        os.makedirs(os.path.dirname(self.handoff))
        with open(self.handoff, "w") as f:
            f.write("# half-written handoff\n")
            f.write("Current task: TBD\n")
            # NO sentinel
        r = _run_refresh(self.root, self.agent, "4h boundary")
        self.assertNotEqual(
            r.returncode, 0,
            "handoff without sentinel must block refresh "
            "(prevents half-finished handoffs from passing)",
        )
        self.assertIn("missing sentinel", r.stderr)
        self.assertFalse(os.path.exists(self.flag))

        # 3. Handoff with sentinel → refresh succeeds, flag
        # written atomically (just verify it appeared with
        # the reason content; mktemp+mv guarantees no partial
        # read but we can't easily test that here).
        with open(self.handoff, "a") as f:
            f.write("\n--- HANDOFF COMPLETE ---\n")
        r = _run_refresh(self.root, self.agent, "4h boundary")
        self.assertEqual(
            r.returncode, 0,
            f"valid handoff should allow refresh: "
            f"{r.stderr}",
        )
        self.assertTrue(
            os.path.exists(self.flag),
            "flag file should be written after success",
        )
        with open(self.flag) as f:
            content = f.read()
        self.assertIn("4h boundary", content)

        # 4. Path-traversal in agent name must be rejected
        # (the script's regex guard)
        r = _run_refresh(
            self.root, "../../etc/passwd", "x"
        )
        self.assertNotEqual(
            r.returncode, 0,
            "path-traversal agent name must be rejected",
        )
        self.assertIn(
            "Invalid agent name", r.stderr
        )


if __name__ == "__main__":
    unittest.main()
