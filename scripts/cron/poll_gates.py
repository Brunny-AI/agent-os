#!/usr/bin/env python3
"""Poll-prompt active-task + parallel-work gates.

Reads `task_engine.py --json-status` from stdin and emits one
of four gate tokens on stdout:

    OK                         active task with fresh artifact
    ACTIVE-TASK-REQUIRED       no IN_PROGRESS task at all
    STALE-ARTIFACT             active task but no recent artifact
    PARALLEL-TASK-REQUIRED     solo IN_PROGRESS + blocked too long

Exit code: 0 on OK, 1 otherwise. Detail (which task, how stale)
goes to stderr — the prompt's `case` statement reads stdout
only, so detail never pollutes the gate decision.

This script is the structural enforcer that prevents the
heartbeat-without-artifact failure mode: an agent whose poll
runs all 7 steps without producing a single file modification
gets blocked here before the heartbeat can fire.

Stdlib only — no jq, no GNU date, no third-party deps.

Usage:
    python3 scripts/task/engine.py --agent alice --json-status \\
      | python3 scripts/cron/poll_gates.py \\
      --max-age-min 15 --blocked-grace-min 15
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys


def _parse_iso(ts: str | None) -> datetime.datetime | None:
    """Parse ISO 8601 (with Z or offset) into aware datetime.

    Returns None when ts is missing or unparseable so callers
    can treat absence as 'unknown' rather than crashing.
    """
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(
            ts.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def _age_min(
    ts: str | None,
    now: datetime.datetime,
) -> float | None:
    """Minutes between ts and now, or None if unparseable."""
    parsed = _parse_iso(ts)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 60.0


def _last_artifact_ts(task: dict) -> str | None:
    """Return most recent artifact timestamp, or None."""
    artifacts = task.get("artifacts") or []
    if not artifacts:
        return None
    return artifacts[-1].get("timestamp")


def _evaluate(
    state: dict,
    max_age_min: float,
    blocked_grace_min: float,
    now: datetime.datetime,
) -> tuple[str, str]:
    """Return (token, detail) for the current state.

    Token is one of: OK, ACTIVE-TASK-REQUIRED,
    STALE-ARTIFACT, PARALLEL-TASK-REQUIRED.
    """
    tasks = state.get("tasks") or {}
    in_progress = {
        tid: t for tid, t in tasks.items()
        if t.get("state") == "IN_PROGRESS"
    }
    blocked = {
        tid: t for tid, t in tasks.items()
        if t.get("state") == "BLOCKED"
    }

    if not in_progress:
        return (
            "ACTIVE-TASK-REQUIRED",
            f"no IN_PROGRESS task "
            f"(blocked={len(blocked)})",
        )

    # Pick the freshest IN_PROGRESS task. If even THAT one is
    # stale, the agent is idle.
    freshest_age: float | None = None
    freshest_tid: str | None = None
    for tid, task in in_progress.items():
        age = _age_min(_last_artifact_ts(task), now)
        if age is None:
            age = _age_min(task.get("claimed_at"), now)
        if age is None:
            continue
        if freshest_age is None or age < freshest_age:
            freshest_age = age
            freshest_tid = tid

    if freshest_age is None:
        return (
            "STALE-ARTIFACT",
            "could not determine artifact age for any "
            "IN_PROGRESS task",
        )

    if freshest_age > max_age_min:
        return (
            "STALE-ARTIFACT",
            f"freshest IN_PROGRESS task {freshest_tid} "
            f"has no artifact in {freshest_age:.0f} min "
            f"(threshold {max_age_min:.0f})",
        )

    # Solo + blocked > grace = pull a parallel task
    if len(in_progress) == 1 and blocked:
        oldest_block_age: float | None = None
        for task in blocked.values():
            age = _age_min(task.get("blocked_at"), now)
            if age is None:
                continue
            if (
                oldest_block_age is None
                or age > oldest_block_age
            ):
                oldest_block_age = age
        if (
            oldest_block_age is not None
            and oldest_block_age >= blocked_grace_min
        ):
            return (
                "PARALLEL-TASK-REQUIRED",
                f"1 IN_PROGRESS + {len(blocked)} BLOCKED "
                f"(oldest blocked {oldest_block_age:.0f} "
                f"min, threshold "
                f"{blocked_grace_min:.0f})",
            )

    return ("OK", "active task with fresh artifact")


def main() -> None:
    """Read state from stdin, emit gate token to stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-min", type=float, default=15.0,
        help="Stale-artifact threshold (default: 15)",
    )
    parser.add_argument(
        "--blocked-grace-min", type=float, default=15.0,
        help="Min blocked duration before parallel pull",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()
    if not raw.strip():
        print("ACTIVE-TASK-REQUIRED")
        print(
            "empty engine state on stdin", file=sys.stderr
        )
        sys.exit(1)

    try:
        state = json.loads(raw)
    except json.JSONDecodeError as exc:
        print("STALE-ARTIFACT")
        print(
            f"engine JSON parse failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc)
    token, detail = _evaluate(
        state,
        args.max_age_min,
        args.blocked_grace_min,
        now,
    )
    print(token)
    print(detail, file=sys.stderr)
    sys.exit(0 if token == "OK" else 1)


if __name__ == "__main__":
    main()
