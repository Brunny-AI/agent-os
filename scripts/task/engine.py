#!/usr/bin/env python3
"""Finish-to-start transaction enforcer for agent tasks.

Core invariant: complete(task_n) requires exists(task_n+1.claim)
AND exists(task_n+1.first_output).

Task completion is not "I'm done." It is "I have already started
the next thing."

Task states: READY -> CLAIMED -> IN_PROGRESS -> COMPLETE
             CLAIMED/IN_PROGRESS -> BLOCKED | EXPIRED
             CLAIMED/IN_PROGRESS/BLOCKED -> CANCELLED

A task cannot enter COMPLETE unless another task is CLAIMED by
the same agent and at least one artifact exists for that task.

Usage:
    python scripts/task/engine.py --agent alice --claim T-001
    python scripts/task/engine.py --agent alice --complete T-001
    python scripts/task/engine.py --agent alice --status
    python scripts/task/engine.py --agent alice --check-lease
    python scripts/task/engine.py --agent alice --json-status
    python scripts/task/engine.py --agent alice --cancel T-001
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import re
import sys
import tempfile

_AGENT_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
LEASE_MINUTES = 15


def _repo_root() -> str:
    """Resolve the repository root directory."""
    return os.environ.get(
        "AGENT_OS_ROOT",
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )


def _validate_agent(name: str) -> None:
    """Validate agent name against safe pattern."""
    if not _AGENT_RE.match(name):
        print(
            f"Error: invalid agent name '{name}'",
            file=sys.stderr,
        )
        sys.exit(1)


def _engine_path(agent: str) -> str:
    """Return the path to an agent's task engine state."""
    return os.path.join(
        _repo_root(), "workspaces", agent,
        "logs", "progress", "task-engine-state.json",
    )


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load_state(agent: str) -> dict[str, object]:
    """Load task engine state from disk."""
    path = _engine_path(agent)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {
        "tasks": {},
        "initiative_counter": 0,
        "last_updated": None,
    }


def _save_state(agent: str, state: dict[str, object]) -> None:
    """Atomically save task engine state under flock."""
    path = _engine_path(agent)
    state["last_updated"] = _now_iso()
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    lock_path = path + ".lock"
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        fd, tmp = tempfile.mkstemp(dir=parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(
                    state, f, indent=2, ensure_ascii=False
                )
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
        fcntl.flock(lock_f, fcntl.LOCK_UN)


def cmd_claim(args: argparse.Namespace) -> None:
    """Claim a task -- starts the lease clock."""
    state = _load_state(args.agent)
    now = _now_iso()
    expires = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=LEASE_MINUTES)
    ).isoformat()

    if args.claim in state["tasks"]:
        existing = state["tasks"][args.claim]
        if existing["status"] in ("CLAIMED", "IN_PROGRESS"):
            print(
                f"Task {args.claim} already {existing['status']}.",
                file=sys.stderr,
            )
            sys.exit(1)

    state["tasks"][args.claim] = {
        "status": "CLAIMED",
        "claimed_at": now,
        "lease_expires": expires,
        "description": args.claim_desc,
        "first_step": args.claim_first_step,
        "artifacts": [],
        "context_refs": [],
    }
    _save_state(args.agent, state)
    print(f"CLAIMED: {args.claim}")
    print(f"  Lease expires in {LEASE_MINUTES} min")
    step = args.claim_first_step or "(not specified)"
    print(f"  First step: {step}")
    print("  Produce first artifact to enter IN_PROGRESS")


def cmd_artifact(args: argparse.Namespace) -> None:
    """Record an artifact for a task. Renews lease."""
    task_id, artifact_path = args.artifact
    state = _load_state(args.agent)
    if task_id not in state["tasks"]:
        print(
            f"Task {task_id} not found. Claim it first.",
            file=sys.stderr,
        )
        sys.exit(1)

    task = state["tasks"][task_id]
    now = _now_iso()
    task["artifacts"].append({"path": artifact_path, "at": now})
    task["lease_expires"] = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=LEASE_MINUTES)
    ).isoformat()

    if task["status"] == "CLAIMED":
        task["status"] = "IN_PROGRESS"
        task["started_at"] = now
        print(
            f"IN_PROGRESS: {task_id} "
            f"(first artifact, lease renewed)"
        )
    else:
        print(f"ARTIFACT: {task_id} (lease renewed)")

    _save_state(args.agent, state)


def cmd_complete(args: argparse.Namespace) -> None:
    """Complete a task. Requires next task claimed + artifact."""
    state = _load_state(args.agent)
    task_id = args.complete

    if task_id not in state["tasks"]:
        print(f"Task {task_id} not found.", file=sys.stderr)
        sys.exit(1)

    task = state["tasks"][task_id]
    if task["status"] not in ("CLAIMED", "IN_PROGRESS"):
        print(
            f"Cannot complete {task_id}: "
            f"status is {task['status']}. "
            f"Only CLAIMED/IN_PROGRESS tasks can complete.",
            file=sys.stderr,
        )
        sys.exit(1)

    other_active = [
        tid for tid, t in state["tasks"].items()
        if tid != task_id
        and t["status"] in ("CLAIMED", "IN_PROGRESS")
        and len(t.get("artifacts", [])) > 0
    ]

    if not other_active:
        print(
            f"BLOCKED: Cannot complete {task_id}.",
            file=sys.stderr,
        )
        print(
            "  Invariant: complete(task_n) requires "
            "exists(task_n+1.claim) AND "
            "exists(task_n+1.first_output)",
            file=sys.stderr,
        )
        sys.exit(1)

    task["status"] = "COMPLETE"
    task["completed_at"] = _now_iso()

    state["initiative_counter"] = (
        state.get("initiative_counter", 0) + 1
    )
    counter = state["initiative_counter"]
    if counter % 3 == 0:
        print(
            f"!! INITIATIVE REQUIRED: "
            f"{counter} tasks completed."
        )
        print(
            "   Generate 1 self-directed leverage proposal."
        )

    _save_state(args.agent, state)
    print(f"COMPLETE: {task_id}")
    print(f"  Next active: {', '.join(other_active)}")

    _generate_followups(args.agent, task_id, state)


def cmd_block(args: argparse.Namespace) -> None:
    """Mark a task as BLOCKED."""
    state = _load_state(args.agent)
    task_id = args.block

    if task_id not in state["tasks"]:
        print(f"Task {task_id} not found.", file=sys.stderr)
        sys.exit(1)

    task = state["tasks"][task_id]
    task["status"] = "BLOCKED"
    task["blocked_at"] = _now_iso()
    task["blocker_type"] = args.blocker_type
    task["blocker_owner"] = args.blocker_owner
    task["blocked_reason"] = args.block_reason

    _save_state(args.agent, state)
    print(f"BLOCKED: {task_id}")
    print(
        f"  Blocker: {args.blocker_type} "
        f"(owner: {args.blocker_owner})"
    )
    print(
        "  Claim a fallback task from backlogs. "
        "Blocked != idle."
    )


def cmd_cancel(args: argparse.Namespace) -> None:
    """Cancel a stale CLAIMED / IN_PROGRESS / BLOCKED task.

    Cancellation is the graceful exit for tasks that can't
    complete (spec changed, dependency vanished, task turned
    out not to apply). Transitions status → CANCELLED,
    records when and why, preserves the task's history in
    the state file.

    Unlike --complete, cancellation does NOT require a
    follow-up claim — cancelling is always allowed because
    the task isn't shipping anyway.

    COMPLETE and CANCELLED tasks are both terminal; neither
    triggers the finish-to-start invariant downstream.
    """
    state = _load_state(args.agent)
    task_id = args.cancel
    tasks = state.get("tasks")
    if not isinstance(tasks, dict) or task_id not in tasks:
        print(f"Task {task_id} not found.", file=sys.stderr)
        sys.exit(1)

    task = tasks[task_id]
    status = task.get("status")
    # EXPIRED is set by lease-expiry mechanism and represents
    # historical fact (the task ran past its lease); --cancel
    # must not overwrite that with a fresher cancelled_at and
    # mask the actual coast event from the audit trail.
    if status in ("COMPLETE", "CANCELLED", "EXPIRED"):
        print(
            f"Task {task_id} already {status}.",
            file=sys.stderr,
        )
        sys.exit(1)

    task["status"] = "CANCELLED"
    task["cancelled_at"] = _now_iso()
    task["cancelled_reason"] = args.cancel_reason
    _save_state(args.agent, state)
    print(f"CANCELLED: {task_id}")
    reason = args.cancel_reason or "(no reason given)"
    print(f"  Reason: {reason}")


def cmd_check_lease(args: argparse.Namespace) -> None:
    """Check for expired task leases."""
    state = _load_state(args.agent)
    now = datetime.datetime.now(datetime.timezone.utc)
    expired = []

    for tid, task in state["tasks"].items():
        if task["status"] not in ("CLAIMED", "IN_PROGRESS"):
            continue
        lease = task.get("lease_expires")
        if not lease:
            continue
        try:
            expires = datetime.datetime.fromisoformat(
                lease.replace("Z", "+00:00")
            )
            if now > expires:
                expired.append((tid, task))
        except (ValueError, TypeError):
            continue

    if expired:
        for tid, task in expired:
            try:
                exp_time = datetime.datetime.fromisoformat(
                    task["lease_expires"].replace(
                        "Z", "+00:00"
                    )
                )
                age = (
                    (now - exp_time).total_seconds() / 60
                )
            except (ValueError, TypeError):
                age = 0
            print(
                f"!! LEASE EXPIRED: {tid} "
                f"({age:.0f} min overdue)"
            )
            task["status"] = "EXPIRED"
        _save_state(args.agent, state)

    sys.exit(1 if expired else 0)


def cmd_status(args: argparse.Namespace) -> None:
    """Show current task states."""
    state = _load_state(args.agent)
    tasks = state.get("tasks", {})

    if not tasks:
        print(f"  No tasks tracked for {args.agent}.")
        return

    status_order = [
        "IN_PROGRESS", "CLAIMED", "COMPLETE",
        "EXPIRED", "BLOCKED", "CANCELLED",
    ]
    for status in status_order:
        group = [
            (tid, t) for tid, t in tasks.items()
            if t["status"] == status
        ]
        if not group:
            continue
        print(f"\n  {status}:")
        for tid, t in group:
            artifacts = len(t.get("artifacts", []))
            desc = t.get("description", "")[:50]
            print(f"    {tid}: {desc} ({artifacts} artifacts)")
            if (
                t.get("lease_expires")
                and status in ("CLAIMED", "IN_PROGRESS")
            ):
                try:
                    expires = datetime.datetime.fromisoformat(
                        t["lease_expires"].replace(
                            "Z", "+00:00"
                        )
                    )
                    remaining = (
                        (
                            expires
                            - datetime.datetime.now(datetime.timezone.utc)
                        ).total_seconds()
                        / 60
                    )
                    print(
                        f"      Lease: {remaining:.0f} "
                        f"min remaining"
                    )
                except (ValueError, TypeError):
                    pass

    counter = state.get("initiative_counter", 0)
    next_init = 3 - (counter % 3)
    print(
        f"\n  Initiative: {counter} tasks completed, "
        f"next proposal due in {next_init} tasks"
    )


def _generate_followups(
    agent: str,
    task_id: str,
    state: dict[str, object],
) -> None:
    """Print adjacent-possible scan prompts."""
    task = state.get("tasks", {}).get(task_id, {})
    desc = task.get("description", task_id)
    artifacts = task.get("artifacts", [])

    print(f"\nADJACENT-POSSIBLE SCAN -- after: {desc}")
    print("=" * 40)
    print(f"Artifacts produced: {len(artifacts)}")
    for a in artifacts:
        print(f"  - {a.get('path', '?')}")
    print()
    print("Generate 3-5 follow-up candidates:")
    print("  1. What is now INCOMPLETE?")
    print("  2. What is now POSSIBLE?")
    print("  3. What is now STALE?")
    print("  4. What should be AUTOMATED?")
    print("  5. What RISK was exposed?")
    print()
    print(
        "CLAIM the highest-ranked candidate and "
        "start immediately."
    )


def cmd_json_status(args: argparse.Namespace) -> None:
    """Emit structured JSON of task states for poll gates.

    Output schema (stable contract for poll-prompt v4.6+):
      {
        "agent": str,
        "as_of": ISO8601 UTC,
        "tasks": {
          TASK_ID: {
            "state": str  # READY|CLAIMED|IN_PROGRESS|COMPLETE
                          # |EXPIRED|BLOCKED
            "claimed_at": ISO8601 | None,
            "started_at": ISO8601 | None,
            "completed_at": ISO8601 | None,
            "blocked_at": ISO8601 | None,
            "blocker_type": str | None,
            "lease_expires": ISO8601 | None,
            "artifacts": [
              {"path": str, "timestamp": ISO8601}
            ]
          }
        }
      }

    Note: 'state' (not 'status') and artifact 'timestamp' (not
    'at') are the public field names; this isolates consumers
    from internal storage naming.
    """
    state = _load_state(args.agent)
    raw_tasks = state.get("tasks") or {}
    if not isinstance(raw_tasks, dict):
        raw_tasks = {}
    tasks_out: dict[str, dict[str, object]] = {}
    out: dict[str, object] = {
        "agent": args.agent,
        "as_of": _now_iso(),
        "tasks": tasks_out,
    }
    for tid, task in raw_tasks.items():
        tasks_out[tid] = {
            "state": task.get("status"),
            "claimed_at": task.get("claimed_at"),
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
            "blocked_at": task.get("blocked_at"),
            "blocker_type": task.get("blocker_type"),
            "lease_expires": task.get("lease_expires"),
            "artifacts": [
                {
                    "path": a.get("path"),
                    "timestamp": a.get("at"),
                }
                for a in task.get("artifacts", [])
            ],
        }
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_post_ship(args: argparse.Namespace) -> None:
    """Run post-ship cooldown sequence."""
    print("POST-SHIP COOLDOWN SEQUENCE")
    print("=" * 40)
    print("1. VERIFY: Is the shipped work correct?")
    print("2. EXTRACT: What follow-on work exists?")
    print("3. CLAIM: Select highest-leverage next task")
    print("4. STUB: Create first artifact for it")
    print()
    print("No silent post-ship window should exist.")


def main() -> None:
    """Parse arguments and dispatch."""
    parser = argparse.ArgumentParser(
        description="Finish-to-start task engine"
    )
    parser.add_argument(
        "--agent", required=True, help="Agent ID"
    )
    parser.add_argument("--claim", help="Claim a task")
    parser.add_argument(
        "--claim-desc", default="", help="Description"
    )
    parser.add_argument(
        "--claim-first-step", default="",
        help="Exact first step"
    )
    parser.add_argument(
        "--complete", help="Complete a task"
    )
    parser.add_argument(
        "--artifact", nargs=2,
        metavar=("TASK_ID", "PATH"),
        help="Record artifact"
    )
    parser.add_argument(
        "--block", help="Mark task as blocked"
    )
    parser.add_argument(
        "--cancel",
        help="Cancel a stale task (CLAIMED/IN_PROGRESS/BLOCKED)"
    )
    parser.add_argument(
        "--cancel-reason", default="",
        dest="cancel_reason",
        help="Why the task is being cancelled"
    )
    parser.add_argument(
        "--blocker-type", default="unknown",
        help="Blocker type"
    )
    parser.add_argument(
        "--blocker-owner", default="unknown",
        help="Who can unblock"
    )
    parser.add_argument(
        "--block-reason", default="", help="Why blocked"
    )
    parser.add_argument(
        "--check-lease", action="store_true",
        help="Check for expired leases"
    )
    parser.add_argument(
        "--post-ship", action="store_true",
        help="Run post-ship cooldown"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show task states"
    )
    parser.add_argument(
        "--json-status", action="store_true",
        dest="json_status",
        help="Emit structured JSON for poll gates"
    )
    args = parser.parse_args()

    _validate_agent(args.agent)

    if args.claim:
        cmd_claim(args)
    elif args.complete:
        cmd_complete(args)
    elif args.artifact:
        cmd_artifact(args)
    elif args.block:
        cmd_block(args)
    elif args.cancel:
        cmd_cancel(args)
    elif args.check_lease:
        cmd_check_lease(args)
    elif args.post_ship:
        cmd_post_ship(args)
    elif args.status:
        cmd_status(args)
    elif args.json_status:
        cmd_json_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
