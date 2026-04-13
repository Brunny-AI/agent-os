#!/usr/bin/env python3
"""Cron registry manager with heartbeat-based liveness.

Manages agent cron job registration, heartbeats, liveness
checks, and checkout gating. The registry provides cross-session
and cross-agent visibility via heartbeats stored in a shared
JSON file.

CronList (Claude Code built-in) is the source of truth for
the current session. This registry enables cross-agent monitoring.

Usage:
    python scripts/cron/manager.py register alice poll JOB123
    python scripts/cron/manager.py heartbeat alice poll
    python scripts/cron/manager.py status
    python scripts/cron/manager.py checkout alice
    python scripts/cron/manager.py list
    python scripts/cron/manager.py cleanup
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone


def _repo_root() -> str:
    """Resolve the repository root directory."""
    return os.environ.get(
        "AGENT_OS_ROOT",
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )


def _registry_path() -> str:
    """Return the path to the cron registry file."""
    return os.path.join(
        _repo_root(), "system", "cron-registry.json"
    )


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return (
        datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _load_registry(path: str) -> dict[str, object]:
    """Load the cron registry, creating it if absent."""
    if not os.path.exists(path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = {"schema_version": 2, "jobs": []}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        return data
    with open(path) as f:
        return json.load(f)


def _save_registry(
    path: str, data: dict[str, object]
) -> None:
    """Atomically save the registry under flock.

    Note: load + modify + save is not a single atomic
    transaction. Concurrent writers can overwrite each
    other's changes. This is acceptable for MVP since
    agents run one process each and rarely write
    simultaneously. A transactional helper is planned.
    """
    lock_path = path + ".lock"
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        parent = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(dir=parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
        fcntl.flock(lock_f, fcntl.LOCK_UN)


def _find_job(
    jobs: list[dict], record_id: str
) -> dict | None:
    """Find a job by record ID."""
    return next(
        (j for j in jobs if j["id"] == record_id), None
    )


# -- Commands --


def cmd_register(args: argparse.Namespace) -> None:
    """Register a cron job in the registry."""
    path = _registry_path()
    data = _load_registry(path)
    now = _now_iso()

    type_config = {
        "poll": {
            "timeout": 15,
            "cron_desc": "every 5 min",
            "id_fmt": "poll-{agent}",
        },
        "meeting": {
            "timeout": 5,
            "cron_desc": "every 1 min",
            "id_fmt": "meeting-{agent}-{channel}",
        },
        "scheduler": {
            "timeout": 90,
            "cron_desc": "every 60 min",
            "id_fmt": "scheduler-{agent}",
        },
    }

    cfg = type_config[args.type]
    record_id = cfg["id_fmt"].format(
        agent=args.agent,
        channel=getattr(args, "channel", ""),
    )

    existing = _find_job(data["jobs"], record_id)
    if existing:
        existing["session_job_id"] = args.job_id
        existing["registered_at"] = now
        existing["last_heartbeat"] = now
        existing["heartbeat_timeout_min"] = cfg["timeout"]
        existing["cron"] = cfg["cron_desc"]
        existing.pop("checked_out", None)
        if args.type == "meeting":
            existing["channel"] = args.channel
    else:
        rec = {
            "id": record_id,
            "type": args.type,
            "ldap": args.agent,
            "channel": getattr(args, "channel", None),
            "cron": cfg["cron_desc"],
            "session_job_id": args.job_id,
            "registered_at": now,
            "last_heartbeat": now,
            "heartbeat_timeout_min": cfg["timeout"],
        }
        data["jobs"].append(rec)

    _save_registry(path, data)
    extra = ""
    if args.type == "meeting":
        extra = f" on '{args.channel}'"
    print(
        f"Registered {args.type} for {args.agent}{extra} "
        f"(job: {args.job_id}, "
        f"timeout: {cfg['timeout']}m)"
    )


def cmd_heartbeat(args: argparse.Namespace) -> None:
    """Update heartbeat timestamp for a registered job."""
    path = _registry_path()
    data = _load_registry(path)
    now = _now_iso()

    id_fmts = {
        "poll": "poll-{agent}",
        "meeting": "meeting-{agent}-{channel}",
        "scheduler": "scheduler-{agent}",
    }
    record_id = id_fmts[args.type].format(
        agent=args.agent,
        channel=getattr(args, "channel", ""),
    )

    record = _find_job(data["jobs"], record_id)
    if not record:
        print(
            f"No registered job found for {record_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    record["last_heartbeat"] = now
    _save_registry(path, data)
    print(f"Heartbeat: {record_id} at {now}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show all jobs with liveness status."""
    path = _registry_path()
    data = _load_registry(path)
    jobs = data.get("jobs", [])
    now = datetime.now(timezone.utc)

    if not jobs:
        print("No cron jobs registered.")
        return

    active = []
    expired = []
    checked_out = []

    for j in jobs:
        if j.get("checked_out"):
            checked_out.append(j)
            continue
        timeout = j.get("heartbeat_timeout_min", 15)
        last_hb = j.get("last_heartbeat")
        age = None
        is_active = False
        if last_hb:
            try:
                hb_time = datetime.fromisoformat(
                    last_hb.replace("Z", "+00:00")
                )
                age = now - hb_time
                is_active = age < timedelta(
                    minutes=timeout
                )
            except (ValueError, TypeError):
                pass

        if is_active:
            active.append((j, age))
        else:
            expired.append((j, age))

    print("=== Agent OS Cron Status ===")
    print(
        f"  Total: {len(jobs)}  |  "
        f"Active: {len(active)}  |  "
        f"Checked out: {len(checked_out)}  |  "
        f"Expired: {len(expired)}"
    )
    print()

    if active:
        print("ACTIVE")
        for j, age in active:
            ch = (
                f"  channel={j['channel']}"
                if j.get("channel")
                else ""
            )
            age_s = (
                f"{int(age.total_seconds())}s ago"
                if age
                else "?"
            )
            print(
                f"  [{j['type']}] {j['ldap']}{ch}  "
                f"cron={j['cron']}  "
                f"job={j.get('session_job_id', '?')[:8]}  "
                f"heartbeat={age_s}"
            )
        print()

    if checked_out:
        print("CHECKED OUT (intentionally offline)")
        for j in checked_out:
            print(
                f"  [{j['type']}] {j['ldap']}  "
                f"checked_out={j['checked_out']}"
            )
        print()

    if expired:
        print("EXPIRED (no heartbeat)")
        for j, age in expired:
            ch = (
                f"  channel={j['channel']}"
                if j.get("channel")
                else ""
            )
            if age:
                age_s = f"{int(age.total_seconds() / 60)}m ago"
            else:
                age_s = "never"
            note = ""
            if j.get("type") == "scheduler":
                note = (
                    "  (hourly, may be between fires)"
                )
            print(
                f"  [{j['type']}] {j['ldap']}{ch}  "
                f"last_heartbeat={age_s}  "
                f"timeout="
                f"{j.get('heartbeat_timeout_min', '?')}m"
                f"{note}"
            )

    print()
    print(
        "Note: use CronList for live jobs in the "
        "current session."
    )


def cmd_cleanup(args: argparse.Namespace) -> None:
    """Remove expired meeting jobs from the registry."""
    path = _registry_path()
    data = _load_registry(path)
    now = datetime.now(timezone.utc)
    before = len(data.get("jobs", []))
    kept = []
    removed = []

    for j in data.get("jobs", []):
        if j.get("type") != "meeting":
            kept.append(j)
            continue
        timeout = j.get("heartbeat_timeout_min", 5)
        last_hb = j.get("last_heartbeat")
        if last_hb:
            hb_time = datetime.fromisoformat(
                last_hb.replace("Z", "+00:00")
            )
            age = now - hb_time
            if age >= timedelta(minutes=timeout * 2):
                removed.append(j["id"])
                continue
        kept.append(j)

    data["jobs"] = kept
    _save_registry(path, data)

    if removed:
        for r in removed:
            print(f"  Removed: {r}")
        print(
            f"Cleaned up {len(removed)} expired meeting "
            f"jobs ({before} -> {len(kept)})"
        )
    else:
        print("Nothing to clean up.")


def cmd_checkout(args: argparse.Namespace) -> None:
    """Mark an agent as intentionally offline.

    Checks for approval from a designated approver role
    on the event bus before allowing checkout. The approver
    is configurable via config/agent-os.yaml or defaults
    to 'founder'.
    """
    path = _registry_path()
    data = _load_registry(path)
    now = _now_iso()

    # Load checkout approver from config (if available)
    approver_role = "founder"
    config_path = os.path.join(
        _repo_root(), "config", "agent-os.yaml"
    )
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            gov = cfg.get("governance", {})
            approver_role = gov.get(
                "checkout_approver_agent", "founder"
            )
        except ImportError:
            pass

    # Search bus for recent checkout approval scoped
    # to this specific agent
    bus_dir = os.path.join(
        _repo_root(), "system", "bus"
    )
    approved = _check_checkout_approval(
        bus_dir, approver_role, args.agent
    )

    if not approved:
        print(
            "CHECKOUT BLOCKED: No checkout approval "
            f"for '{args.agent}' from '{approver_role}' "
            "found on bus in last 60 min."
        )
        print(
            "  Only the designated approver can authorize "
            "checkout."
        )
        sys.exit(1)

    record = _find_job(data["jobs"], f"poll-{args.agent}")
    if not record:
        print(f"No poll found for {args.agent}")
        return

    record["checked_out"] = now
    _save_registry(path, data)
    print(f"Checked out: poll-{args.agent} at {now}")


def _check_checkout_approval(
    bus_dir: str,
    approver_role: str,
    target_agent: str,
) -> bool:
    """Check if an approver authorized checkout recently.

    Searches the last 60 minutes of bus messages for a
    message from the approver that both contains checkout
    keywords AND names the target agent.

    Args:
        bus_dir: Path to the bus root directory.
        approver_role: Agent ID or role name to match.
        target_agent: Agent requesting checkout (must
            appear in the approval message).

    Returns:
        True if a matching approval message was found.
    """
    import glob

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=60)

    channels_dir = os.path.join(bus_dir, "channels")
    if not os.path.isdir(channels_dir):
        return False

    keywords = [
        "checkout", "check out", "wrap up",
        "shut down", "good night",
    ]

    for channel in os.listdir(channels_dir):
        channel_dir = os.path.join(channels_dir, channel)
        if not os.path.isdir(channel_dir):
            continue
        jsonl_files = sorted(
            glob.glob(
                os.path.join(channel_dir, "*.jsonl")
            )
        )[-2:]
        for jsonl in jsonl_files:
            try:
                with open(jsonl) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        msg = json.loads(line)
                        ts = msg.get("timestamp", "")
                        if ts:
                            msg_time = (
                                datetime.fromisoformat(
                                    ts.replace(
                                        "Z", "+00:00"
                                    )
                                )
                            )
                            if msg_time < cutoff:
                                continue
                        sender = msg.get("from", "")
                        body = msg.get(
                            "body", ""
                        ).lower()
                        if sender != approver_role:
                            continue
                        has_keyword = any(
                            k in body for k in keywords
                        )
                        has_agent = (
                            target_agent.lower() in body
                            or "all" in body
                        )
                        if has_keyword and has_agent:
                            return True
            except (
                json.JSONDecodeError,
                KeyError,
                ValueError,
            ):
                continue
    return False


def cmd_list(args: argparse.Namespace) -> None:
    """List all registered jobs with details."""
    path = _registry_path()
    data = _load_registry(path)
    jobs = data.get("jobs", [])
    now = datetime.now(timezone.utc)

    if not jobs:
        print("No cron jobs registered.")
        return

    by_agent: dict[str, list[dict]] = {}
    for j in jobs:
        ldap = j.get("ldap", "?")
        by_agent.setdefault(ldap, []).append(j)

    print("=== Registered Cron Jobs ===")
    print()

    for ldap in sorted(by_agent.keys()):
        agent_jobs = by_agent[ldap]
        print(f"  {ldap}:")
        for j in agent_jobs:
            co = j.get("checked_out")
            if co:
                state = "checked-out"
            else:
                timeout = j.get(
                    "heartbeat_timeout_min", 15
                )
                last_hb = j.get("last_heartbeat")
                if last_hb:
                    hb_time = datetime.fromisoformat(
                        last_hb.replace("Z", "+00:00")
                    )
                    age = now - hb_time
                    if age < timedelta(minutes=timeout):
                        state = "active"
                    else:
                        state = "expired"
                else:
                    state = "never-seen"

            last_hb = j.get("last_heartbeat")
            if last_hb:
                hb_time = datetime.fromisoformat(
                    last_hb.replace("Z", "+00:00")
                )
                secs = int(
                    (now - hb_time).total_seconds()
                )
                if secs < 60:
                    elapsed = f"{secs}s ago"
                elif secs < 3600:
                    elapsed = f"{secs // 60}m ago"
                else:
                    h = secs // 3600
                    m = (secs % 3600) // 60
                    elapsed = f"{h}h {m}m ago"
            else:
                elapsed = "never"

            jtype = j.get("type", "?")
            job_id = j.get(
                "session_job_id", "?"
            )[:8]
            channel = j.get("channel", "")
            print(
                f"    [{jtype}] {j['id']}  ({state})"
            )
            print(
                f"      cadence:  {j.get('cron', '?')}"
            )
            if channel:
                print(f"      channel:  {channel}")
            print(f"      last run: {elapsed}")
            print()

    print(
        f"Total: {len(jobs)} job(s) across "
        f"{len(by_agent)} agent(s)"
    )


def main() -> None:
    """Parse arguments and dispatch to subcommand."""
    parser = argparse.ArgumentParser(
        description="Agent OS cron registry manager"
    )
    sub = parser.add_subparsers(dest="command")

    # register
    p_reg = sub.add_parser(
        "register", help="Register a cron job"
    )
    p_reg.add_argument("agent", help="Agent ID")
    p_reg.add_argument(
        "type", choices=["poll", "meeting", "scheduler"]
    )
    p_reg.add_argument(
        "job_id_or_channel",
        help="Job ID (poll/scheduler) or channel (meeting)"
    )
    p_reg.add_argument(
        "job_id_extra", nargs="?", default=None,
        help="Job ID (only for meeting type)"
    )

    # heartbeat
    p_hb = sub.add_parser(
        "heartbeat", help="Send heartbeat"
    )
    p_hb.add_argument("agent", help="Agent ID")
    p_hb.add_argument(
        "type", choices=["poll", "meeting", "scheduler"]
    )
    p_hb.add_argument(
        "channel", nargs="?", default=None,
        help="Channel (meeting type only)"
    )

    # status
    sub.add_parser(
        "status", help="Show liveness status"
    )

    # list
    sub.add_parser(
        "list", help="List all jobs with details"
    )

    # cleanup
    sub.add_parser(
        "cleanup", help="Remove expired meeting jobs"
    )

    # checkout
    p_co = sub.add_parser(
        "checkout", help="Mark agent as offline"
    )
    p_co.add_argument("agent", help="Agent ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Normalize register args
    if args.command == "register":
        if args.type == "meeting":
            args.channel = args.job_id_or_channel
            args.job_id = args.job_id_extra
            if not args.job_id:
                print(
                    "Error: meeting requires "
                    "<channel> <job_id>",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            args.job_id = args.job_id_or_channel

    dispatch = {
        "register": cmd_register,
        "heartbeat": cmd_heartbeat,
        "status": cmd_status,
        "list": cmd_list,
        "cleanup": cmd_cleanup,
        "checkout": cmd_checkout,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
