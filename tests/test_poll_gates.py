"""poll_gates.py: all 4 gate tokens + edge cases.

Locks the gate's contract — what it consumes (stdin JSON shape
from `task_engine.py --json-status`) and what it emits
(stdout = single token, stderr = detail, exit = 0|1). Poll
prompts shell-out via this contract; if it ever drifts, the
v4.6 active-task gate breaks silently.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import typing
import unittest


_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_GATE = os.path.join(
    _REPO, "scripts", "cron", "poll_gates.py"
)


def _now_iso(offset_min: float = 0.0) -> str:
    """Return an ISO8601 UTC timestamp with an offset.

    Args:
        offset_min: Minutes to add to wall clock (negative for
            past timestamps used in stale-artifact tests).

    Returns:
        ISO8601 string with UTC offset, e.g.
        '2026-04-18T05:00:00+00:00'.
    """
    t = datetime.datetime.now(
        datetime.timezone.utc
    ) + datetime.timedelta(minutes=offset_min)
    return t.isoformat()


def _run(
    state: dict[str, typing.Any], *args: str,
) -> tuple[str, str, int]:
    """Pipe state JSON to poll_gates.py via stdin.

    Args:
        state: Engine state dict to feed into poll_gates.py
            (matches the --json-status output schema).
        *args: Extra CLI flags (e.g. '--max-age-min', '5').

    Returns:
        Tuple of (stdout, stderr, returncode), all stripped.
    """
    result = subprocess.run(
        [sys.executable, _GATE, *args],
        input=json.dumps(state),
        capture_output=True,
        text=True,
        check=False,
    )
    return (
        result.stdout.strip(),
        result.stderr.strip(),
        result.returncode,
    )


def _state(
    tasks: dict[str, dict[str, typing.Any]],
) -> dict[str, typing.Any]:
    """Wrap a tasks dict in the json-status envelope."""
    return {
        "agent": "alice",
        "as_of": _now_iso(),
        "tasks": tasks,
    }


class PollGatesContractTest(unittest.TestCase):
    """Each test pins a single gate path. Fails loud if the
    contract drifts (stdout token, stderr presence, exit code)."""

    def test_ok_when_active_task_has_fresh_artifact(self) -> None:
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "out.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        out, err, rc = _run(state)
        self.assertEqual(out, "OK")
        self.assertEqual(rc, 0)
        # Detail should still go to stderr even on OK
        self.assertIn("active task", err)

    def test_active_task_required_when_no_in_progress(
        self,
    ) -> None:
        state = _state({
            "T-DONE": {"state": "COMPLETE", "artifacts": []}
        })
        out, err, rc = _run(state)
        self.assertEqual(out, "ACTIVE-TASK-REQUIRED")
        self.assertEqual(rc, 1)
        self.assertIn("no IN_PROGRESS", err)

    def test_stale_artifact_when_age_exceeds_threshold(
        self,
    ) -> None:
        # Artifact 30 min old, threshold is default 15 min.
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "out.py", "timestamp": _now_iso(-30)}
                ],
            }
        })
        out, err, rc = _run(state)
        self.assertEqual(out, "STALE-ARTIFACT")
        self.assertEqual(rc, 1)
        self.assertIn("30 min", err)

    def test_parallel_required_when_solo_and_blocked_old(
        self,
    ) -> None:
        # 1 fresh IN_PROGRESS + 1 BLOCKED >15 min ago.
        state = _state({
            "T-WORK": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-1)}
                ],
            },
            "T-WAIT": {
                "state": "BLOCKED",
                "blocked_at": _now_iso(-30),
            },
        })
        out, err, rc = _run(state)
        self.assertEqual(out, "PARALLEL-TASK-REQUIRED")
        self.assertEqual(rc, 1)
        self.assertIn("BLOCKED", err)

    def test_stale_artifact_takes_precedence_over_parallel(
        self,
    ) -> None:
        # Both conditions true — stale-artifact must fire first
        # (Gate A before Gate B).
        state = _state({
            "T-WORK": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-30)}
                ],
            },
            "T-WAIT": {
                "state": "BLOCKED",
                "blocked_at": _now_iso(-30),
            },
        })
        out, _, rc = _run(state)
        self.assertEqual(out, "STALE-ARTIFACT")
        self.assertEqual(rc, 1)

    def test_two_in_progress_skips_parallel_gate(self) -> None:
        # Solo+blocked is the trigger; with 2 IN_PROGRESS we
        # already have parallel work and Gate B is moot.
        state = _state({
            "T-A": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "a.py", "timestamp": _now_iso(-1)}
                ],
            },
            "T-B": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "b.py", "timestamp": _now_iso(-1)}
                ],
            },
            "T-WAIT": {
                "state": "BLOCKED",
                "blocked_at": _now_iso(-30),
            },
        })
        out, _, rc = _run(state)
        self.assertEqual(out, "OK")
        self.assertEqual(rc, 0)

    def test_empty_stdin_is_active_task_required(self) -> None:
        # Defensive: a misconfigured pipeline (empty stdin)
        # must NOT silently emit OK. Block the heartbeat.
        result = subprocess.run(
            [sys.executable, _GATE],
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.stdout.strip(), "ACTIVE-TASK-REQUIRED"
        )
        self.assertEqual(result.returncode, 1)

    def test_malformed_json_is_stale_artifact(self) -> None:
        # Defensive: don't trust upstream blindly. Malformed
        # JSON blocks the heartbeat with STALE-ARTIFACT (we
        # can't tell freshness, treat as not-fresh).
        result = subprocess.run(
            [sys.executable, _GATE],
            input="this is not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.stdout.strip(), "STALE-ARTIFACT"
        )
        self.assertEqual(result.returncode, 1)

    def test_custom_thresholds_via_flags(self) -> None:
        # Artifact 10 min old, default threshold 15 → OK.
        # With --max-age-min 5 → STALE.
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-10)}
                ],
            }
        })
        out, _, rc = _run(state)
        self.assertEqual(out, "OK")
        out, _, rc = _run(state, "--max-age-min", "5")
        self.assertEqual(out, "STALE-ARTIFACT")


if __name__ == "__main__":
    unittest.main()
