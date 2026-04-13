#!/usr/bin/env python3
"""Check agent output by file modification timestamps.

Scans an agent's workspace for recently modified files,
excluding poll maintenance files. Reports whether the agent
has produced real output in the last N minutes.

Status levels:
  BUILDING: has git commits (shipped work)
  WORKING:  file modifications but no commits (in-progress)
  STALE:    same files for 3+ polls (gaming the clock)
  IDLE:     no commits and no file modifications

Usage:
    python scripts/monitor/output_clock.py --agent alice
    python scripts/monitor/output_clock.py --all --json
    python scripts/monitor/output_clock.py --all --minutes 30
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

_AGENT_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _repo_root() -> str:
    """Resolve the repository root directory."""
    return os.environ.get(
        "AGENT_OS_ROOT",
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )


EXCLUDED_FILES = {
    "bus-offsets.json",
    "bus-offsets.json.lock",
    "CLAUDE.md",
    ".DS_Store",
}

EXCLUDED_PATH_PATTERNS = [
    "/system/bus/receipts/",
    "/system/bus/channels/",
    "/memory/bus-offsets.json",
    "/system/cron-registry.json",
]

EXCLUDED_EXTENSIONS = {".pyc", ".pyo", ".lock"}


def _get_agents() -> list[str]:
    """Read agent list from registry."""
    registry = os.path.join(
        _repo_root(), "config", "registry.yaml"
    )
    agents: list[str] = []
    try:
        with open(registry) as f:
            for line in f:
                line = line.strip()
                if line.startswith("- ldap:"):
                    agents.append(
                        line.split(":", 1)[1].strip()
                    )
    except FileNotFoundError:
        pass
    return agents


def _is_excluded(filepath: str) -> bool:
    """Check if a file is infrastructure (not real output)."""
    basename = os.path.basename(filepath)
    if basename in EXCLUDED_FILES:
        return True
    if basename.startswith("."):
        return True
    _, ext = os.path.splitext(basename)
    if ext in EXCLUDED_EXTENSIONS:
        return True
    for pattern in EXCLUDED_PATH_PATTERNS:
        if pattern in filepath:
            return True
    return False


def _load_stale_state(
    agent: str,
) -> dict[str, object]:
    """Load previous poll's file snapshot."""
    cache_dir = os.path.join(
        _repo_root(), "system", "cache"
    )
    state_file = os.path.join(
        cache_dir, f"output-clock-{agent}.json"
    )
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"files": [], "stale_count": 0}


def _save_stale_state(
    agent: str,
    files_snapshot: list[str],
    stale_count: int,
) -> None:
    """Save current file snapshot for stale detection."""
    cache_dir = os.path.join(
        _repo_root(), "system", "cache"
    )
    os.makedirs(cache_dir, exist_ok=True)
    state_file = os.path.join(
        cache_dir, f"output-clock-{agent}.json"
    )
    with open(state_file, "w") as f:
        json.dump(
            {"files": files_snapshot,
             "stale_count": stale_count},
            f,
        )


def _check_git_commits(
    agent: str, minutes: int
) -> list[str]:
    """Check for git commits by this agent recently."""
    workspaces_dir = os.path.join(
        _repo_root(), "workspaces"
    )
    git_dir = os.path.join(workspaces_dir, ".git")
    if not os.path.isdir(git_dir):
        return []

    try:
        result = subprocess.run(
            [
                "git", "-C", workspaces_dir, "log",
                f"--since={minutes} minutes ago",
                f"--grep=\\[{re.escape(agent)}\\]",
                "--oneline",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = [
            line.strip()
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]
        return lines
    except (subprocess.TimeoutExpired, OSError):
        return []


def _scan_workspace(
    agent: str, minutes: int
) -> tuple[str, list[dict[str, object]], list[str]]:
    """Scan agent workspace for recent file modifications.

    Returns:
        Tuple of (status, modified_files, git_commits).
    """
    if not _AGENT_RE.match(agent):
        return "NOT_FOUND", [], []

    root = _repo_root()
    workspace = os.path.join(root, "workspaces", agent)
    if not os.path.isdir(workspace):
        return "NOT_FOUND", [], []

    cutoff = time.time() - (minutes * 60)
    modified_files: list[dict[str, object]] = []

    for dirpath, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            fpath = os.path.join(dirpath, fname)
            if _is_excluded(fpath):
                continue
            try:
                mtime = os.path.getmtime(fpath)
                if mtime >= cutoff:
                    rel = os.path.relpath(fpath, root)
                    modified_files.append({
                        "path": rel,
                        "modified": datetime.fromtimestamp(
                            mtime, tz=timezone.utc
                        ).isoformat(),
                        "minutes_ago": round(
                            (time.time() - mtime) / 60, 1
                        ),
                    })
            except OSError:
                continue

    modified_files.sort(key=lambda x: x["minutes_ago"])

    git_commits = _check_git_commits(agent, minutes)

    # Stale detection
    current = sorted(
        [f"{f['path']}|{f['modified']}" for f in modified_files]
    )
    prev = _load_stale_state(agent)
    prev_files = sorted(prev.get("files", []))
    prev_count = prev.get("stale_count", 0)

    if modified_files and current == prev_files:
        stale_count = prev_count + 1
    else:
        stale_count = 0

    _save_stale_state(agent, current, stale_count)

    if git_commits:
        status = "BUILDING"
    elif not modified_files:
        status = "IDLE"
    elif stale_count >= 3:
        status = "STALE"
    else:
        status = "WORKING"

    return status, modified_files, git_commits


def _check_agent(
    agent: str,
    minutes: int,
    as_json: bool = False,
) -> dict[str, object]:
    """Check one agent and return result dict."""
    status, files, commits = _scan_workspace(
        agent, minutes
    )

    out: dict[str, object] = {
        "agent": agent,
        "status": status,
        "files_modified": len(files),
        "git_commits": len(commits),
        "minutes_checked": minutes,
        "files": files[:10],
        "commits": commits[:5],
    }

    if not as_json:
        if status == "IDLE":
            print(
                f"!! {agent}: IDLE -- no output in "
                f"{minutes} min"
            )
        elif status == "STALE":
            print(
                f"!! {agent}: STALE -- same files "
                f"for 3+ polls"
            )
        elif status == "WORKING":
            print(
                f"   {agent}: WORKING -- "
                f"{len(files)} files, 0 commits"
            )
        elif status == "BUILDING":
            print(
                f"   {agent}: BUILDING -- "
                f"{len(commits)} commits, "
                f"{len(files)} files"
            )
        elif status == "NOT_FOUND":
            print(f"   {agent}: NOT_FOUND")

    return out


def main() -> None:
    """Parse arguments and check agent output."""
    parser = argparse.ArgumentParser(
        description="Check agent output by file timestamps"
    )
    parser.add_argument("--agent", help="Agent ID")
    parser.add_argument(
        "--all", action="store_true",
        help="Check all agents"
    )
    parser.add_argument(
        "--minutes", type=int, default=60,
        help="Look-back window (default: 60)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="JSON output"
    )
    args = parser.parse_args()

    if not args.agent and not args.all:
        parser.error("Specify --agent or --all")

    agents = (
        _get_agents() if args.all else [args.agent]
    )
    results = []

    for agent in agents:
        result = _check_agent(
            agent, args.minutes, as_json=args.json
        )
        results.append(result)

    if args.json:
        output = results if args.all else results[0]
        print(json.dumps(output, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
