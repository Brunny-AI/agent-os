#!/usr/bin/env python3
"""Create a new agent-bus channel.

Creates a channel directory with a manifest and an empty weekly
log file. Appends an entry to the channel index.

Usage:
    python scripts/bus/new_channel.py --name standup --owner alice
    python scripts/bus/new_channel.py \\
        --name review-sprint --type meeting --owner alice
    python scripts/bus/new_channel.py \\
        --name standup --owner alice --attendees all
"""

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone


def week_key() -> str:
    """Return the current ISO week key.

    Returns:
        ISO week string like '2026-W15'.
    """
    return datetime.now(timezone.utc).strftime("%G-W%V")


def main() -> None:
    """Parse arguments and create a channel."""
    parser = argparse.ArgumentParser(
        description="Create a new agent-bus channel"
    )
    parser.add_argument(
        "--name", required=True,
        help="Channel name (lowercase, hyphen-separated)"
    )
    parser.add_argument(
        "--owner", required=True, help="Owner agent ID"
    )
    parser.add_argument(
        "--type", default="async",
        choices=["async", "meeting"],
        help="Channel type (default: async)"
    )
    parser.add_argument(
        "--attendees", default="all",
        help="Required attendees, comma-separated or 'all'"
    )
    parser.add_argument(
        "--desc", default="", help="Channel description"
    )
    parser.add_argument(
        "--bus", default="system/bus",
        help="Bus root directory (default: system/bus)"
    )
    args = parser.parse_args()

    name_clean = args.name.replace("-", "")
    if not name_clean.isalnum() or args.name != args.name.lower():
        print(
            f"Error: channel name must be lowercase and "
            f"hyphen-separated, got '{args.name}'",
            file=sys.stderr,
        )
        sys.exit(1)

    channel_dir = os.path.join(
        args.bus, "channels", args.name
    )
    if os.path.exists(channel_dir):
        print(
            f"Error: channel '{args.name}' already exists",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(channel_dir)

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week = week_key()

    if args.attendees == "all":
        attendees = ["all"]
    else:
        attendees = [
            a.strip() for a in args.attendees.split(",")
        ]

    manifest = {
        "schema_version": 1,
        "name": args.name,
        "type": args.type,
        "owner": args.owner,
        "required_attendees": attendees,
        "created": today,
        "description": (
            args.desc
            or f"{args.type.capitalize()} channel "
            f"owned by {args.owner}"
        ),
    }
    with open(os.path.join(channel_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    open(os.path.join(channel_dir, f"{week}.jsonl"), "w").close()

    index_path = os.path.join(args.bus, "channels", "index.jsonl")
    index_entry = {
        "schema_version": 1,
        "created": now.isoformat().replace("+00:00", "Z"),
        "channel": args.name,
        "type": args.type,
        "owner": args.owner,
    }
    with open(index_path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(index_entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)

    print(f"Created channel: {args.name}")
    print(f"  type:     {args.type}")
    print(f"  owner:    {args.owner}")
    print(f"  week:     {week}")
    print(f"  manifest: {channel_dir}/manifest.json")
    print(f"  log:      {channel_dir}/{week}.jsonl")
    print(f"  index:    {index_path} (appended)")


if __name__ == "__main__":
    main()
