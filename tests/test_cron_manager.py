"""Cron manager: register/heartbeat/expire + checkout-gate (INC-008).

Per Kai's spec-test-suite.md: 2 tests covering the registry's
core promises — heartbeats decay to EXPIRED on their own, and
checkout cannot proceed without an explicit founder bus message
(the INC-008 fix that prevents agents from self-checking-out).
"""

from __future__ import annotations

import datetime
import json
import os
import unittest

from tests import _fixtures


def _mgr(
    root: str, *args: str
) -> "subprocess.CompletedProcess":  # noqa: F821
    """Invoke cron manager with AGENT_OS_ROOT pointing at root."""
    return _fixtures.run_script(
        "scripts/cron/manager.py", *args,
        env_extra={"AGENT_OS_ROOT": root},
    )


def _registry_path(root: str) -> str:
    return os.path.join(root, "system", "cron-registry.json")


class CronManagerLivenessTest(unittest.TestCase):
    """Heartbeat-based liveness: ACTIVE while fresh, EXPIRED when stale."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_register_heartbeat_expire(self) -> None:
        # Register a poll for alice
        r = _mgr(
            self.root, "register", "alice", "poll", "JOB-1"
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(
            "Registered poll for alice", r.stdout
        )

        # Status: should show ACTIVE
        r = _mgr(self.root, "status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ACTIVE", r.stdout)
        self.assertIn("alice", r.stdout)

        # Backdate heartbeat by 20 min — exceeds 15-min poll
        # timeout from cmd_register.type_config.
        path = _registry_path(self.root)
        with open(path) as f:
            data = json.load(f)
        old_hb = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=20)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        for j in data["jobs"]:
            if j["id"] == "poll-alice":
                j["last_heartbeat"] = old_hb
        with open(path, "w") as f:
            json.dump(data, f)

        # Status: should now show EXPIRED
        r = _mgr(self.root, "status")
        self.assertIn(
            "EXPIRED", r.stdout,
            "20-min-old heartbeat should be EXPIRED "
            "(timeout is 15)",
        )

        # Heartbeat brings it back to ACTIVE
        r = _mgr(
            self.root, "heartbeat", "alice", "poll"
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Heartbeat: poll-alice", r.stdout)
        r = _mgr(self.root, "status")
        self.assertIn("ACTIVE", r.stdout)


class CronManagerCheckoutGateTest(unittest.TestCase):
    """INC-008: checkout requires an explicit founder bus msg.

    No agent may self-check-out. Even a registered, healthy
    poll must produce a founder bus message authorizing the
    specific agent before checkout succeeds.
    """

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        _fixtures.mk_channel(self.root, "standup")

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def _send_bus(
        self, channel: str, sender: str, body: str
    ) -> None:
        result = _fixtures.run_script(
            "scripts/bus/send.py",
            "--channel", channel,
            "--from", sender,
            "--body", body,
            "--bus", os.path.join(
                self.root, "system", "bus"
            ),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"send.py failed: {result.stderr}"
            )

    def test_checkout_requires_founder_bus_msg(self) -> None:
        # Register so checkout has something to flip
        _mgr(
            self.root, "register", "alice", "poll", "JOB-A"
        )

        # Attempt checkout WITHOUT founder authorization
        r = _mgr(self.root, "checkout", "alice")
        self.assertNotEqual(
            r.returncode, 0,
            "checkout without founder bus msg must fail",
        )
        self.assertIn("CHECKOUT BLOCKED", r.stdout)

        # Verify nothing was flipped on disk
        with open(_registry_path(self.root)) as f:
            data = json.load(f)
        rec = next(
            j for j in data["jobs"] if j["id"] == "poll-alice"
        )
        self.assertNotIn(
            "checked_out", rec,
            "registry should NOT mark checked_out when "
            "blocked",
        )

        # Wrong-agent message must NOT authorize
        # (specificity matters — INC-008's "checkout bob"
        # doesn't authorize alice).
        self._send_bus(
            "standup", "founder",
            "checkout bob — done for the day"
        )
        r = _mgr(self.root, "checkout", "alice")
        self.assertNotEqual(
            r.returncode, 0,
            "checkout msg naming bob must not authorize "
            "alice",
        )

        # Wrong-sender (peer) must NOT authorize
        self._send_bus(
            "standup", "kai",
            "checkout alice — wrap up"
        )
        r = _mgr(self.root, "checkout", "alice")
        self.assertNotEqual(
            r.returncode, 0,
            "checkout msg from non-founder must not "
            "authorize",
        )

        # Founder + named agent + keyword = authorized
        self._send_bus(
            "standup", "founder",
            "checkout alice — wrap up for the night"
        )
        r = _mgr(self.root, "checkout", "alice")
        self.assertEqual(
            r.returncode, 0,
            f"founder msg with keyword + agent must "
            f"authorize: {r.stdout} {r.stderr}",
        )
        self.assertIn(
            "Checked out: poll-alice", r.stdout
        )

        # Registry now reflects checked_out
        with open(_registry_path(self.root)) as f:
            data = json.load(f)
        rec = next(
            j for j in data["jobs"] if j["id"] == "poll-alice"
        )
        self.assertIn("checked_out", rec)


if __name__ == "__main__":
    unittest.main()
