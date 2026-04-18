"""Output clock: WORKING → STALE after 3 polls without change.

Per Kai's spec-test-suite.md: stale_count climbs while file
snapshot is unchanged. After 3 unchanged polls, status flips
from WORKING to STALE — the gaming detector for agents who
re-touch the same file every poll without producing real work.
"""

from __future__ import annotations

import json
import os
import time
import unittest

from tests import _fixtures


def _scan(
    root: str, agent: str
) -> dict:
    """Run output_clock JSON scan for one agent and parse."""
    result = _fixtures.run_script(
        "scripts/monitor/output_clock.py",
        "--agent", agent,
        "--minutes", "30",
        "--json",
        env_extra={"AGENT_OS_ROOT": root},
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"output_clock failed: {result.stderr}"
        )
    return json.loads(result.stdout)


class OutputClockStaleTransitionTest(unittest.TestCase):
    """3 consecutive unchanged snapshots flips WORKING → STALE."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        self.agent = "alice"
        self.workspace = os.path.join(
            self.root, "workspaces", self.agent
        )
        os.makedirs(
            os.path.join(self.workspace, "logs"),
            exist_ok=True,
        )
        # Touch a file so we have SOMETHING to track
        self.tracked = os.path.join(
            self.workspace, "logs", "activity.md"
        )
        with open(self.tracked, "w") as f:
            f.write("# initial entry\n")

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_working_to_stale_transition(self) -> None:
        # Poll 1: file is fresh → WORKING (stale_count=0)
        r = _scan(self.root, self.agent)
        self.assertEqual(
            r["status"], "WORKING",
            f"poll 1 expected WORKING, got {r['status']}",
        )

        # Polls 2 + 3: same files, stale_count climbs
        # but stays under threshold
        for poll_n in (2, 3):
            r = _scan(self.root, self.agent)
            self.assertEqual(
                r["status"], "WORKING",
                f"poll {poll_n}: expected WORKING (still "
                f"under stale threshold), got {r['status']}",
            )

        # Poll 4: stale_count >= 3 → STALE
        r = _scan(self.root, self.agent)
        self.assertEqual(
            r["status"], "STALE",
            "poll 4: 3 unchanged snapshots should flip to "
            "STALE (gaming detector)",
        )

        # Now MODIFY the file — stale_count must reset to 0
        # and the next poll should be WORKING again
        time.sleep(1)  # ensure mtime changes
        with open(self.tracked, "a") as f:
            f.write("\n# new work\n")
        r = _scan(self.root, self.agent)
        self.assertEqual(
            r["status"], "WORKING",
            f"after real modification, status should reset "
            f"to WORKING, got {r['status']}",
        )


if __name__ == "__main__":
    unittest.main()
