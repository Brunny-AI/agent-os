"""poll_gates.py --log-file + gate_audit.py round-trip.

Exercises the instrumentation path end-to-end: feed the gate
a known state, verify the JSONL entry shape matches what
gate_audit.py consumes, then run the audit and check the
summary counts the invocation correctly.

Without --log-file, no file is written (backwards compat).
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import typing
import unittest


_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_GATE = os.path.join(
    _REPO, "scripts", "cron", "poll_gates.py"
)
_AUDIT = os.path.join(
    _REPO, "scripts", "monitor", "gate_audit.py"
)


def _now_iso(offset_min: float = 0.0) -> str:
    """ISO 8601 UTC timestamp with offset in minutes."""
    t = datetime.datetime.now(
        datetime.timezone.utc
    ) + datetime.timedelta(minutes=offset_min)
    return t.isoformat()


def _run_gate(
    state: dict[str, typing.Any], *args: str,
) -> tuple[str, str, int]:
    """Pipe state JSON to poll_gates.py.

    Returns (stdout, stderr, returncode) all stripped.
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
    agent: str = "alice",
) -> dict[str, typing.Any]:
    """Wrap tasks in the json-status envelope."""
    return {
        "agent": agent,
        "as_of": _now_iso(),
        "tasks": tasks,
    }


class GateLoggingTest(unittest.TestCase):
    """Gate writes JSONL record only when --log-file is set."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(
            shutil.rmtree, self.tmp, ignore_errors=True
        )
        self.log = os.path.join(self.tmp, "audit.jsonl")

    def test_no_log_without_flag(self) -> None:
        """Backwards compat: no --log-file → no file."""
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        out, _, rc = _run_gate(state)
        self.assertEqual(out, "OK")
        self.assertEqual(rc, 0)
        self.assertFalse(
            os.path.exists(self.log),
            "log file appeared without --log-file flag",
        )

    def test_log_written_on_ok(self) -> None:
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        out, _, rc = _run_gate(state, "--log-file", self.log)
        self.assertEqual(out, "OK")
        self.assertEqual(rc, 0)
        with open(self.log, encoding="utf-8") as handle:
            lines = [
                line for line in handle
                if line.strip()
            ]
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["token"], "OK")
        self.assertEqual(entry["agent"], "alice")
        self.assertEqual(entry["freshest_task"], "T-1")
        self.assertEqual(entry["in_progress_count"], 1)
        self.assertEqual(entry["blocked_count"], 0)
        self.assertIn("ts", entry)
        self.assertTrue(entry["ts"].endswith("Z"))
        self.assertEqual(
            entry["thresholds"]["max_age_min"], 15.0
        )

    def test_log_written_on_stale(self) -> None:
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {
                        "path": "x.py",
                        "timestamp": _now_iso(-30),
                    }
                ],
            }
        })
        out, _, rc = _run_gate(state, "--log-file", self.log)
        self.assertEqual(out, "STALE-ARTIFACT")
        self.assertEqual(rc, 1)
        with open(self.log, encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip())
        self.assertEqual(entry["token"], "STALE-ARTIFACT")
        self.assertGreater(entry["freshest_age_min"], 15)

    def test_log_appends_across_invocations(self) -> None:
        """Two sequential runs → two lines in the log."""
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        _run_gate(state, "--log-file", self.log)
        _run_gate(state, "--log-file", self.log)
        with open(self.log, encoding="utf-8") as handle:
            lines = [
                line for line in handle
                if line.strip()
            ]
        self.assertEqual(len(lines), 2)
        for line in lines:
            entry = json.loads(line)
            self.assertEqual(entry["token"], "OK")

    def test_log_creates_parent_dirs(self) -> None:
        nested = os.path.join(
            self.tmp, "a", "b", "audit.jsonl"
        )
        state = _state({
            "T-DONE": {"state": "COMPLETE", "artifacts": []}
        })
        _run_gate(state, "--log-file", nested)
        self.assertTrue(pathlib.Path(nested).exists())

    def test_log_failure_does_not_block_gate(self) -> None:
        """Fail-open: unwritable log must not eat the token.

        Regression for the original instrumentation code path
        that crashed with an OSError before printing the gate
        decision. The poll prompt's `case` statement reads
        stdout; if main() raises before print(), behavior is
        undefined.
        """
        ro_dir = os.path.join(self.tmp, "readonly")
        os.makedirs(ro_dir)
        os.chmod(ro_dir, 0o555)
        self.addCleanup(os.chmod, ro_dir, 0o755)
        unwritable = os.path.join(ro_dir, "audit.jsonl")
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        out, err, rc = _run_gate(
            state, "--log-file", unwritable,
        )
        self.assertEqual(out, "OK")
        self.assertEqual(rc, 0)
        self.assertIn("audit log write failed", err)

    def test_concurrent_appends_preserve_lines(self) -> None:
        """flock + flush + fsync under the lock serializes
        writes so each subprocess's line reaches disk before
        another acquires the lock. No interleaved partial
        lines; no lost writes.
        """
        state = _state({
            "T-1": {
                "state": "IN_PROGRESS",
                "artifacts": [
                    {"path": "x.py", "timestamp": _now_iso(-2)}
                ],
            }
        })
        procs = [
            subprocess.Popen(
                [sys.executable, _GATE,
                 "--log-file", self.log],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(10)
        ]
        for proc in procs:
            proc.communicate(input=json.dumps(state))
        with open(self.log, encoding="utf-8") as handle:
            lines = [
                line for line in handle if line.strip()
            ]
        self.assertEqual(len(lines), 10)
        for line in lines:
            # No interleaved partial JSON:
            self.assertTrue(line.strip().startswith("{"))
            self.assertTrue(line.rstrip().endswith("}"))
            # Each line parses cleanly:
            entry = json.loads(line)
            self.assertEqual(entry["token"], "OK")

    def test_empty_stdin_path_is_logged(self) -> None:
        """Regression: empty-stdin used to exit before the
        logging hook, making those gate fires invisible to
        gate_audit. Now the emit helper logs all exit paths.
        """
        proc = subprocess.run(
            [sys.executable, _GATE,
             "--log-file", self.log],
            input="",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.stdout.strip(),
                         "ACTIVE-TASK-REQUIRED")
        self.assertEqual(proc.returncode, 1)
        with open(self.log, encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip())
        self.assertEqual(entry["token"],
                         "ACTIVE-TASK-REQUIRED")
        self.assertEqual(entry["agent"], "unknown")
        self.assertIn("empty engine state", entry["detail"])

    def test_json_parse_fail_path_is_logged(self) -> None:
        """Regression: malformed JSON on stdin used to exit
        before logging. Now recorded as STALE-ARTIFACT with
        the parse error in detail.
        """
        proc = subprocess.run(
            [sys.executable, _GATE,
             "--log-file", self.log],
            input="this is not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.stdout.strip(),
                         "STALE-ARTIFACT")
        self.assertEqual(proc.returncode, 1)
        with open(self.log, encoding="utf-8") as handle:
            entry = json.loads(handle.read().strip())
        self.assertEqual(entry["token"], "STALE-ARTIFACT")
        self.assertEqual(entry["agent"], "unknown")
        self.assertIn("engine JSON parse failed",
                      entry["detail"])


class GateAuditWindowTest(unittest.TestCase):
    """gate_audit.py parses ISO timestamps before computing
    min/max for the summary window. Raw string comparison
    would misorder mixed `Z` and `+00:00` suffixes.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(
            shutil.rmtree, self.tmp, ignore_errors=True
        )
        self.log = os.path.join(self.tmp, "audit.jsonl")

    def test_corrupt_lines_warn_but_still_exit_zero(
        self,
    ) -> None:
        """Corrupt JSONL lines warn to stderr, but the audit
        run still exits 0 — docstring now reflects that disk-
        unreadable is the only exit-1 path. Clean counts
        preserved from the parseable lines.
        """
        with open(self.log, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "ts": _now_iso(), "agent": "alice",
                "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 1.0,
                "in_progress_count": 1,
                "blocked_count": 0,
            }) + "\n")
            handle.write("this is not json\n")
            handle.write("{not parseable\n")
        proc = subprocess.run(
            [sys.executable,
             os.path.join(_REPO, "scripts", "monitor",
                          "gate_audit.py"),
             "--log-file", self.log,
             "--days", "1"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("2 malformed JSONL", proc.stderr)
        self.assertIn("Total invocations: 1", proc.stdout)

    def test_mixed_tz_suffix_window_bounds(self) -> None:
        """Entry with `+00:00` suffix should not be
        ordered before an earlier `Z`-suffixed entry
        purely because `+` < `Z` in ASCII.
        """
        earlier_z = "2026-04-18T01:00:00Z"
        later_offset = "2026-04-18T02:00:00+00:00"
        with open(self.log, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "ts": earlier_z, "agent": "alice",
                "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 1.0,
                "in_progress_count": 1,
                "blocked_count": 0,
            }) + "\n")
            handle.write(json.dumps({
                "ts": later_offset, "agent": "alice",
                "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 1.0,
                "in_progress_count": 1,
                "blocked_count": 0,
            }) + "\n")
        proc = subprocess.run(
            [sys.executable,
             os.path.join(_REPO, "scripts", "monitor",
                          "gate_audit.py"),
             "--log-file", self.log,
             "--days", "365", "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0)
        summary = json.loads(proc.stdout)
        # window_start is the earlier entry (01:00Z),
        # window_end the later (02:00+00:00). Not sorted
        # by raw string order.
        self.assertTrue(
            summary["window_start"].startswith(
                "2026-04-18T01:00:00"
            )
        )
        self.assertTrue(
            summary["window_end"].startswith(
                "2026-04-18T02:00:00"
            )
        )


class GateAuditTest(unittest.TestCase):
    """gate_audit.py reads JSONL from the gate, emits summary."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(
            shutil.rmtree, self.tmp, ignore_errors=True
        )
        self.log = os.path.join(self.tmp, "audit.jsonl")

    def _run_audit(
        self, *args: str,
    ) -> tuple[str, str, int]:
        result = subprocess.run(
            [sys.executable, _AUDIT, *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return (
            result.stdout,
            result.stderr,
            result.returncode,
        )

    def _write_log(
        self, entries: list[dict[str, typing.Any]],
    ) -> None:
        with open(self.log, "w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")

    def test_missing_log_exits_1(self) -> None:
        missing = os.path.join(self.tmp, "nope.jsonl")
        _, err, rc = self._run_audit(
            "--log-file", missing, "--days", "1",
        )
        self.assertEqual(rc, 1)
        self.assertIn("no log", err)

    def test_text_summary_counts_tokens_and_agents(
        self,
    ) -> None:
        now = _now_iso()
        recent = _now_iso(-60)
        self._write_log([
            {
                "ts": now, "agent": "alice", "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 2.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
            {
                "ts": now, "agent": "alice", "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 3.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
            {
                "ts": recent, "agent": "bob",
                "token": "STALE-ARTIFACT",
                "freshest_task": "T-9",
                "freshest_age_min": 22.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
        ])
        out, _, rc = self._run_audit(
            "--log-file", self.log, "--days", "1",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Total invocations: 3", out)
        self.assertIn("OK: 2", out)
        self.assertIn("STALE-ARTIFACT: 1", out)
        self.assertIn("alice:", out)
        self.assertIn("bob:", out)

    def test_json_mode_returns_parseable_dict(self) -> None:
        self._write_log([
            {
                "ts": _now_iso(), "agent": "alice",
                "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 2.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
        ])
        out, _, rc = self._run_audit(
            "--log-file", self.log, "--days", "1", "--json",
        )
        self.assertEqual(rc, 0)
        summary = json.loads(out)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["by_token"]["OK"], 1)
        self.assertIn("alice", summary["by_agent"])

    def test_days_window_filters_old_entries(self) -> None:
        """Entries older than --days should be excluded."""
        now_ts = _now_iso()
        old_ts = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=30)
        ).isoformat()
        self._write_log([
            {
                "ts": now_ts, "agent": "alice",
                "token": "OK",
                "freshest_task": "T-1",
                "freshest_age_min": 2.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
            {
                "ts": old_ts, "agent": "alice",
                "token": "STALE-ARTIFACT",
                "freshest_task": "T-OLD",
                "freshest_age_min": 99.0,
                "in_progress_count": 1, "blocked_count": 0,
            },
        ])
        out, _, rc = self._run_audit(
            "--log-file", self.log, "--days", "1",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Total invocations: 1", out)
        self.assertIn("OK: 1", out)
        self.assertNotIn("STALE-ARTIFACT", out)


if __name__ == "__main__":
    unittest.main()
