"""Shared test helpers — temp workspaces and subprocess wrappers.

Per Kai's spec-test-suite.md: each test creates a tempdir,
writes fixture files, invokes the component as a subprocess,
asserts the result, and tears down. Stdlib only — no pytest,
no pip install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)


def mk_temp_workspace() -> str:
    """Return a tempdir that mimics post-setup.py layout.

    Creates the directory skeleton that components expect (bus
    channels dir, workspaces dir, .claude/rules dir). Tests
    write their own fixture data into these paths. Caller owns
    cleanup via cleanup() or shutil.rmtree.
    """
    root = tempfile.mkdtemp(prefix="agent-os-test-")
    os.makedirs(
        os.path.join(root, "system", "bus", "channels")
    )
    os.makedirs(os.path.join(root, "system", "bus", "receipts"))
    os.makedirs(os.path.join(root, "workspaces"))
    os.makedirs(os.path.join(root, ".claude", "rules"))
    return root


def cleanup(root: str) -> None:
    """Remove a temp workspace; ignore missing paths."""
    shutil.rmtree(root, ignore_errors=True)


def mk_channel(root: str, name: str) -> str:
    """Create an empty bus channel and return its path."""
    path = os.path.join(root, "system", "bus", "channels", name)
    os.makedirs(path, exist_ok=True)
    return path


def run_script(
    script_rel: str,
    *args: str,
    cwd: str | None = None,
    env_extra: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Invoke a repo script via subprocess, return the result.

    Args:
        script_rel: Path relative to repo root, e.g.
            "scripts/bus/send.py".
        *args: Arguments passed to the script.
        cwd: Working directory for the subprocess. Defaults to
            REPO so 'system/bus' relative paths resolve.
        env_extra: Extra environment variables (merged with
            os.environ).
        check: If True, raise CalledProcessError on non-zero
            exit (default: False — tests inspect returncode).

    Returns:
        subprocess.CompletedProcess with stdout/stderr captured.
    """
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, os.path.join(REPO, script_rel), *args],
        capture_output=True,
        text=True,
        cwd=cwd or REPO,
        env=env,
        check=check,
    )
