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
import fcntl
import json
import pathlib
import sys
from typing import Any


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


def _last_artifact_ts(task: dict[str, Any]) -> str | None:
    """Return most recent artifact timestamp, or None."""
    artifacts = task.get("artifacts") or []
    if not artifacts:
        return None
    return artifacts[-1].get("timestamp")


def _evaluate(
    state: dict[str, Any],
    max_age_min: float,
    blocked_grace_min: float,
    now: datetime.datetime,
) -> tuple[str, str, dict[str, Any]]:
    """Compute the gate token from a task-engine state snapshot.

    Args:
        state: Output of `task/engine.py --json-status` parsed
            into a dict. Must have `tasks` keyed by task ID with
            per-task `state` ("IN_PROGRESS"/"BLOCKED"/etc),
            `claimed_at`, `blocked_at`, and `artifacts` (each
            with `timestamp`).
        max_age_min: Stale-artifact threshold. An IN_PROGRESS
            task whose freshest artifact is older than this
            triggers STALE-ARTIFACT.
        blocked_grace_min: Solo-with-blocked grace period.
            Triggers PARALLEL-TASK-REQUIRED past this.
        now: Wall-clock anchor. Caller passes datetime.now() so
            tests can pin time without monkey-patching.

    Returns:
        Tuple `(token, detail, context)`. Token is one of OK,
        ACTIVE-TASK-REQUIRED, STALE-ARTIFACT, or
        PARALLEL-TASK-REQUIRED. Detail is a human-readable
        sentence sent to stderr by the caller (never to stdout
        — the prompt's `case` statement reads stdout only).
        Context is a dict with structured fields for logging:
        `freshest_task`, `freshest_age_min`, `in_progress_count`,
        `blocked_count`, `oldest_block_age_min`.
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
    context: dict[str, Any] = {
        "freshest_task": None,
        "freshest_age_min": None,
        "in_progress_count": len(in_progress),
        "blocked_count": len(blocked),
        "oldest_block_age_min": None,
    }

    if not in_progress:
        return (
            "ACTIVE-TASK-REQUIRED",
            f"no IN_PROGRESS task "
            f"(blocked={len(blocked)})",
            context,
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

    context["freshest_task"] = freshest_tid
    context["freshest_age_min"] = freshest_age

    if freshest_age is None:
        return (
            "STALE-ARTIFACT",
            "could not determine artifact age for any "
            "IN_PROGRESS task",
            context,
        )

    if freshest_age > max_age_min:
        return (
            "STALE-ARTIFACT",
            f"freshest IN_PROGRESS task {freshest_tid} "
            f"has no artifact in {freshest_age:.0f} min "
            f"(threshold {max_age_min:.0f})",
            context,
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
        context["oldest_block_age_min"] = oldest_block_age
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
                context,
            )

    return ("OK", "active task with fresh artifact", context)


def _append_log(
    log_file: str,
    agent: str,
    token: str,
    detail: str,
    context: dict[str, Any],
    max_age_min: float,
    blocked_grace_min: float,
    now: datetime.datetime,
) -> None:
    """Append one JSONL gate-fire record to the audit log.

    The log is a flat JSONL file; each invocation appends a
    single line. Concurrent polls from multiple agents share
    the same file — fcntl.flock serializes writes so a
    partial line can never end up on disk.

    Args:
        log_file: Path to the JSONL log. Parent directory is
            created if missing.
        agent: Agent whose poll invoked the gate. Lives at the
            top level of the task-engine state dict.
        token: Gate decision token (OK, ACTIVE-TASK-REQUIRED,
            STALE-ARTIFACT, or PARALLEL-TASK-REQUIRED).
        detail: Human-readable sentence from _evaluate.
        context: Structured state from _evaluate — freshest
            task, counts, etc.
        max_age_min: Stale-artifact threshold in effect.
        blocked_grace_min: Parallel-task grace in effect.
        now: Invocation timestamp (tz-aware UTC).

    Raises:
        OSError: If the log file cannot be opened or the
            lock cannot be acquired.
    """
    entry = {
        "ts": now.isoformat().replace("+00:00", "Z"),
        "agent": agent,
        "token": token,
        "detail": detail,
        "freshest_task": context.get("freshest_task"),
        "freshest_age_min": context.get("freshest_age_min"),
        "in_progress_count": context.get("in_progress_count"),
        "blocked_count": context.get("blocked_count"),
        "oldest_block_age_min": context.get(
            "oldest_block_age_min"
        ),
        "thresholds": {
            "max_age_min": max_age_min,
            "blocked_grace_min": blocked_grace_min,
        },
    }
    path = pathlib.Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(json.dumps(entry) + "\n")
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
    parser.add_argument(
        "--log-file", type=str, default=None,
        help=(
            "If set, append a JSONL record per invocation "
            "to this path for gate-audit analysis. Parent "
            "dirs are created. Safe under concurrent polls "
            "(flock). Disabled when unset (default)."
        ),
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
    token, detail, context = _evaluate(
        state,
        args.max_age_min,
        args.blocked_grace_min,
        now,
    )
    if args.log_file:
        _append_log(
            args.log_file,
            state.get("agent", "unknown"),
            token,
            detail,
            context,
            args.max_age_min,
            args.blocked_grace_min,
            now,
        )
    print(token)
    print(detail, file=sys.stderr)
    sys.exit(0 if token == "OK" else 1)


if __name__ == "__main__":
    main()
