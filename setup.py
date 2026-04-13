#!/usr/bin/env python3
"""Agent OS setup script.

Scaffolds a working multi-agent environment from config.
Creates runtime directories, agent workspaces, bus channels,
and installs git hooks.

Usage:
    python3 setup.py init              # Full setup
    python3 setup.py init --dry-run    # Show what would be created
    python3 setup.py validate          # Check existing setup
    python3 setup.py status            # Show current state
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

# Import config loader from the same repo
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__))
)
import re

from scripts.config.loader import load_config, get_value

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _repo_root() -> str:
    """Resolve the repository root directory."""
    return os.environ.get(
        "AGENT_OS_ROOT",
        os.path.dirname(os.path.abspath(__file__)),
    )


def _safe_path(root: str, relative: str) -> str:
    """Join and validate a path stays under root.

    Prevents path traversal via config values like
    '../../.ssh' or absolute paths.
    """
    full = os.path.normpath(
        os.path.join(root, relative)
    )
    root_norm = os.path.normpath(root)
    if not full.startswith(root_norm + os.sep) and full != root_norm:
        print(
            f"Error: path '{relative}' escapes root",
            file=sys.stderr,
        )
        sys.exit(1)
    return full


def _validate_name(name: str) -> None:
    """Validate an agent/channel name."""
    if not _SAFE_NAME_RE.match(name):
        print(
            f"Error: invalid name '{name}'",
            file=sys.stderr,
        )
        sys.exit(1)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize Agent OS environment."""
    root = _repo_root()
    config = load_config(root)
    dry_run = args.dry_run

    print("Agent OS Setup")
    print("=" * 40)

    if dry_run:
        print("DRY RUN -- no changes will be made\n")

    # 1. Create runtime directories
    paths = config.get("paths", {})
    bus_root_rel = paths.get("bus_root", "system/bus")
    runtime_dirs = [
        bus_root_rel,
        os.path.join(bus_root_rel, "channels"),
        os.path.join(bus_root_rel, "receipts"),
        paths.get("cache_dir", "system/cache"),
        paths.get("workspaces", "workspaces"),
    ]

    print("1. Runtime directories")
    for d in runtime_dirs:
        full = _safe_path(root, d)
        if os.path.exists(full):
            print(f"   [exists] {d}/")
        elif dry_run:
            print(f"   [would create] {d}/")
        else:
            os.makedirs(full, exist_ok=True)
            print(f"   [created] {d}/")

    # 2. Create agent workspaces
    team = config.get("team", {})
    agents = team.get("agents", [])

    print(f"\n2. Agent workspaces ({len(agents)} agents)")
    workspaces_dir = _safe_path(
        root, paths.get("workspaces", "workspaces")
    )

    for agent in agents:
        if isinstance(agent, dict):
            name = agent.get("name", "agent")
            role = agent.get("role", "builder")
        else:
            name = str(agent)
            role = "builder"

        _validate_name(name)
        agent_dir = os.path.join(workspaces_dir, name)
        subdirs = [
            "logs/activity",
            "logs/progress",
            "logs/shift",
            "memory",
            "scratch",
        ]

        if os.path.exists(agent_dir):
            print(f"   [exists] {name}/ ({role})")
        elif dry_run:
            print(f"   [would create] {name}/ ({role})")
        else:
            for sub in subdirs:
                os.makedirs(
                    os.path.join(agent_dir, sub),
                    exist_ok=True,
                )

            # Write agent profile stub
            profile = os.path.join(agent_dir, "profile.md")
            with open(profile, "w") as f:
                f.write(
                    f"# {name}\n\n"
                    f"Role: {role}\n"
                    f"Created: {_now_iso()}\n\n"
                    f"Complete this profile before "
                    f"starting work.\n"
                )

            # Write CLAUDE.md stub
            claude_md = os.path.join(agent_dir, "CLAUDE.md")
            with open(claude_md, "w") as f:
                f.write(
                    f"# {name} ({role})\n\n"
                    f"Read profile.md at session start.\n"
                )

            # Initialize empty task engine state
            engine_state = os.path.join(
                agent_dir, "logs", "progress",
                "task-engine-state.json",
            )
            with open(engine_state, "w") as f:
                json.dump(
                    {
                        "tasks": {},
                        "initiative_counter": 0,
                        "last_updated": _now_iso(),
                    },
                    f, indent=2,
                )
                f.write("\n")

            # Initialize bus offsets
            offsets_path = os.path.join(
                agent_dir, "memory", "bus-offsets.json"
            )
            with open(offsets_path, "w") as f:
                json.dump(
                    {"schema_version": 1, "offsets": {}},
                    f, indent=2,
                )
                f.write("\n")

            print(f"   [created] {name}/ ({role})")

    # 3. Create default bus channels
    print("\n3. Bus channels")
    bus_root = _safe_path(
        root, paths.get("bus_root", "system/bus")
    )
    channels_dir = os.path.join(bus_root, "channels")
    default_channels = ["standup", "urgent"]

    for ch_name in default_channels:
        ch_dir = os.path.join(channels_dir, ch_name)
        if os.path.exists(ch_dir):
            print(f"   [exists] {ch_name}")
        elif dry_run:
            print(f"   [would create] {ch_name}")
        else:
            os.makedirs(ch_dir, exist_ok=True)
            week = datetime.now(timezone.utc).strftime(
                "%G-W%V"
            )
            manifest = {
                "schema_version": 1,
                "name": ch_name,
                "type": "async",
                "owner": "system",
                "required_attendees": ["all"],
                "created": datetime.now(timezone.utc)
                .strftime("%Y-%m-%d"),
                "description": f"Default {ch_name} channel",
            }
            with open(
                os.path.join(ch_dir, "manifest.json"), "w"
            ) as f:
                json.dump(manifest, f, indent=2)
                f.write("\n")
            open(
                os.path.join(ch_dir, f"{week}.jsonl"), "w"
            ).close()

            # Append to index
            index_path = os.path.join(
                channels_dir, "index.jsonl"
            )
            entry = {
                "schema_version": 1,
                "created": _now_iso(),
                "channel": ch_name,
                "type": "async",
                "owner": "system",
            }
            with open(index_path, "a") as f:
                f.write(json.dumps(entry) + "\n")

            print(f"   [created] {ch_name}")

    # 4. Initialize cron registry
    print("\n4. Cron registry")
    registry_path = _safe_path(
        root,
        paths.get(
            "cron_registry", "system/cron-registry.json"
        ),
    )
    if os.path.exists(registry_path):
        print("   [exists] cron-registry.json")
    elif dry_run:
        print("   [would create] cron-registry.json")
    else:
        parent = os.path.dirname(registry_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(registry_path, "w") as f:
            json.dump(
                {"schema_version": 2, "jobs": []},
                f, indent=2,
            )
            f.write("\n")
        print("   [created] cron-registry.json")

    # 5. Install git hooks
    print("\n5. Git hooks")
    hooks_src = os.path.join(root, "scripts", "hooks")
    hooks_dst = os.path.join(root, ".git", "hooks")

    if not os.path.isdir(os.path.join(root, ".git")):
        print("   [skip] not a git repository")
    elif not os.path.isdir(hooks_src):
        print("   [skip] scripts/hooks/ not found")
    else:
        for hook in ["pre-commit", "pre-push"]:
            src = os.path.join(hooks_src, hook)
            dst = os.path.join(hooks_dst, hook)
            if not os.path.exists(src):
                continue
            if os.path.exists(dst):
                print(f"   [exists] {hook}")
            elif dry_run:
                print(f"   [would install] {hook}")
            else:
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)
                print(f"   [installed] {hook}")

    # 6. Write registry.yaml for agent list
    print("\n6. Agent registry")
    config_dir = _safe_path(
        root, paths.get("config", "config")
    )
    registry_yaml = os.path.join(
        config_dir, "registry.yaml"
    )
    if os.path.exists(registry_yaml):
        print("   [exists] config/registry.yaml")
    elif dry_run:
        print("   [would create] config/registry.yaml")
    else:
        os.makedirs(config_dir, exist_ok=True)
        with open(registry_yaml, "w") as f:
            f.write("# Agent Registry\n")
            f.write(f"# Generated: {_now_iso()}\n\n")
            f.write("agents:\n")
            for agent in agents:
                if isinstance(agent, dict):
                    name = agent.get("name", "agent")
                    role = agent.get("role", "builder")
                else:
                    name = str(agent)
                    role = "builder"
                f.write(f'  - ldap: "{name}"\n')
                f.write(f'    role: "{role}"\n')
        print("   [created] config/registry.yaml")

    print("\n" + "=" * 40)
    if dry_run:
        print("Dry run complete. No changes made.")
    else:
        print("Setup complete!")
        print(
            f"\nTeam: {team.get('name', 'default')} "
            f"({len(agents)} agents)"
        )
        print(
            "Run 'python3 setup.py status' to verify."
        )


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate the current setup."""
    root = _repo_root()
    config = load_config(root)
    errors: list[str] = []
    warnings: list[str] = []

    paths = config.get("paths", {})
    bus_root = _safe_path(
        root, paths.get("bus_root", "system/bus")
    )
    workspaces = _safe_path(
        root, paths.get("workspaces", "workspaces")
    )

    # Check runtime dirs
    for d in [bus_root, workspaces]:
        if not os.path.isdir(d):
            errors.append(f"Missing directory: {d}")

    # Check agents
    team = config.get("team", {})
    agents = team.get("agents", [])
    for agent in agents:
        name = (
            agent.get("name") if isinstance(agent, dict)
            else str(agent)
        )
        agent_dir = os.path.join(workspaces, name)
        if not os.path.isdir(agent_dir):
            errors.append(
                f"Missing workspace: {name}/"
            )
        else:
            profile = os.path.join(
                agent_dir, "profile.md"
            )
            if not os.path.exists(profile):
                warnings.append(
                    f"{name}: missing profile.md"
                )

    # Check bus channels
    channels_dir = os.path.join(bus_root, "channels")
    for ch in ["standup", "urgent"]:
        if not os.path.isdir(
            os.path.join(channels_dir, ch)
        ):
            errors.append(
                f"Missing bus channel: {ch}"
            )

    # Check git hooks
    hooks_dir = os.path.join(root, ".git", "hooks")
    for hook in ["pre-commit", "pre-push"]:
        if os.path.isdir(
            os.path.join(root, ".git")
        ) and not os.path.exists(
            os.path.join(hooks_dir, hook)
        ):
            warnings.append(
                f"Git hook not installed: {hook}"
            )

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    if not errors and not warnings:
        print("Validation passed.")

    sys.exit(1 if errors else 0)


def cmd_status(args: argparse.Namespace) -> None:
    """Show current Agent OS status."""
    root = _repo_root()
    config = load_config(root)
    paths = config.get("paths", {})
    team = config.get("team", {})
    agents = team.get("agents", [])

    print("=== Agent OS Status ===\n")
    print(f"Root: {root}")
    print(f"Team: {team.get('name', '?')}")
    print(f"Agents: {len(agents)}")
    print()

    workspaces = _safe_path(
        root, paths.get("workspaces", "workspaces")
    )
    for agent in agents:
        name = (
            agent.get("name") if isinstance(agent, dict)
            else str(agent)
        )
        role = (
            agent.get("role", "?")
            if isinstance(agent, dict)
            else "?"
        )
        agent_dir = os.path.join(workspaces, name)
        exists = os.path.isdir(agent_dir)
        print(
            f"  {name} ({role}): "
            f"{'ready' if exists else 'NOT SET UP'}"
        )

    print()
    bus_root = _safe_path(
        root, paths.get("bus_root", "system/bus")
    )
    channels_dir = os.path.join(bus_root, "channels")
    if os.path.isdir(channels_dir):
        channels = [
            d for d in os.listdir(channels_dir)
            if os.path.isdir(
                os.path.join(channels_dir, d)
            )
        ]
        print(f"Bus channels: {len(channels)}")
    else:
        print("Bus: NOT SET UP")


def main() -> None:
    """Parse arguments and dispatch."""
    parser = argparse.ArgumentParser(
        description="Agent OS setup"
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser(
        "init", help="Initialize environment"
    )
    p_init.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be created"
    )

    sub.add_parser(
        "validate", help="Validate setup"
    )
    sub.add_parser(
        "status", help="Show current status"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "init": cmd_init,
        "validate": cmd_validate,
        "status": cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
