"""Tests for task engine --json-status output contract.

Locks the public schema that poll-prompt v4.6+ gates depend on:
  - 'state' field (not internal 'status')
  - artifact 'timestamp' field (not internal 'at')
  - top-level 'agent' and 'as_of' keys present
  - All known optional fields present (null when absent)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest


_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_ENGINE = os.path.join(_REPO, "scripts", "task", "engine.py")


def _run(agent: str, root: str, *args: str) -> str:
    """Run engine.py with given args and AGENT_OS_ROOT, return stdout."""
    env = dict(os.environ)
    env["AGENT_OS_ROOT"] = root
    result = subprocess.run(
        [sys.executable, _ENGINE, "--agent", agent, *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"engine failed ({result.returncode}): "
            f"{result.stderr}"
        )
    return result.stdout


class JsonStatusContractTest(unittest.TestCase):
    """The shape consumed by poll-prompt v4.6 gate bash."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.agent = "alice"

    def test_empty_state_produces_well_formed_envelope(self) -> None:
        out = _run(self.agent, self.tmp, "--json-status")
        data = json.loads(out)
        self.assertEqual(data["agent"], self.agent)
        self.assertIn("as_of", data)
        self.assertEqual(data["tasks"], {})

    def test_claimed_then_artifact_emits_in_progress(self) -> None:
        _run(
            self.agent, self.tmp, "--claim", "T-1",
            "--claim-desc", "first task",
            "--claim-first-step", "write hello",
        )
        _run(
            self.agent, self.tmp,
            "--artifact", "T-1", "out/hello.py",
        )
        data = json.loads(
            _run(self.agent, self.tmp, "--json-status")
        )
        task = data["tasks"]["T-1"]
        # Public field names per contract:
        self.assertEqual(task["state"], "IN_PROGRESS")
        self.assertIsNotNone(task["lease_expires"])
        self.assertEqual(len(task["artifacts"]), 1)
        artifact = task["artifacts"][0]
        self.assertEqual(artifact["path"], "out/hello.py")
        self.assertIn("timestamp", artifact)
        # Internal storage names must NOT leak:
        self.assertNotIn("status", task)
        self.assertNotIn("at", artifact)

    def test_blocked_task_exposes_blocker_metadata(self) -> None:
        _run(
            self.agent, self.tmp, "--claim", "T-2",
            "--claim-desc", "blocked task",
        )
        _run(
            self.agent, self.tmp, "--block", "T-2",
            "--blocker-type", "review",
            "--blocker-owner", "kai",
            "--block-reason", "waiting on PR review",
        )
        data = json.loads(
            _run(self.agent, self.tmp, "--json-status")
        )
        task = data["tasks"]["T-2"]
        self.assertEqual(task["state"], "BLOCKED")
        self.assertEqual(task["blocker_type"], "review")
        self.assertIsNotNone(task["blocked_at"])

    def test_optional_fields_are_null_not_missing(self) -> None:
        # Gate B uses null-vs-value checks, so missing keys would
        # break jq selectors (.value.blocked_at != null).
        _run(
            self.agent, self.tmp, "--claim", "T-3",
            "--claim-desc", "claimed only",
        )
        data = json.loads(
            _run(self.agent, self.tmp, "--json-status")
        )
        task = data["tasks"]["T-3"]
        for key in (
            "state", "claimed_at", "started_at",
            "completed_at", "blocked_at", "blocker_type",
            "lease_expires", "artifacts",
        ):
            self.assertIn(key, task, f"missing key: {key}")


if __name__ == "__main__":
    unittest.main()
