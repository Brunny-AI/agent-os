#!/usr/bin/env python3
"""Close the current week and open the next one.

Writes a snapshot summary message to each active channel, then
creates next week's empty log file. Intended for the coordinator
agent to run at the end of each ISO week.

Usage:
    python scripts/bus/snapshot.py --from coordinator
    python scripts/bus/snapshot.py --from coordinator \\
        --summary "Shipped agent-bus v0.1."
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone


def week_key(dt: datetime | None = None) -> str:
    """Return the ISO week key for a given datetime.

    Args:
        dt: Datetime to compute the week key for.
            Defaults to now (UTC).

    Returns:
        ISO week string like '2026-W15'.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%G-W%V")


def next_week_key() -> str:
    """Return the ISO week key for next week."""
    now = datetime.now(timezone.utc)
    return week_key(now + timedelta(weeks=1))


def main() -> None:
    """Parse arguments and rotate weekly logs."""
    parser = argparse.ArgumentParser(
        description="Close current week and open next week"
    )
    parser.add_argument(
        "--from", dest="sender", required=True,
        help="Coordinator agent ID"
    )
    parser.add_argument(
        "--summary", default="",
        help="Week summary appended to each snapshot"
    )
    parser.add_argument(
        "--bus", default="system/bus",
        help="Bus root directory (default: system/bus)"
    )
    args = parser.parse_args()

    channels_dir = os.path.join(args.bus, "channels")
    current_week = week_key()
    nxt_week = next_week_key()
    now = datetime.now(timezone.utc)

    print(
        f"Closing week {current_week}, "
        f"opening {nxt_week}...\n"
    )

    for channel in sorted(os.listdir(channels_dir)):
        if channel == "index.jsonl":
            continue
        channel_dir = os.path.join(channels_dir, channel)
        if not os.path.isdir(channel_dir):
            continue

        current_log = os.path.join(
            channel_dir, f"{current_week}.jsonl"
        )
        next_log = os.path.join(
            channel_dir, f"{nxt_week}.jsonl"
        )

        if not os.path.exists(current_log):
            continue

        with open(current_log) as f:
            msg_count = sum(
                1 for line in f if line.strip()
            )

        body = (
            f"Week {current_week} closed. "
            f"{msg_count} messages."
        )
        if args.summary:
            body += f" {args.summary}"

        snapshot_msg = {
            "schema_version": 1,
            "id": f"{args.sender}_snapshot_{current_week}",
            "channel": channel,
            "type": "snapshot",
            "from": args.sender,
            "to": ["all"],
            "timestamp": now.isoformat().replace(
                "+00:00", "Z"
            ),
            "ttl_hours": 8760,
            "body": body,
        }
        with open(current_log, "a") as f:
            f.write(json.dumps(snapshot_msg) + "\n")

        if not os.path.exists(next_log):
            open(next_log, "w").close()

        print(
            f"  {channel}: snapshot written, "
            f"{nxt_week}.jsonl created"
        )

    print(
        f"\nDone. All channels rotated to week {nxt_week}."
    )


if __name__ == "__main__":
    main()
