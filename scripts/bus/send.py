#!/usr/bin/env python3
"""Send a message to an agent-bus channel.

Usage:
    python scripts/bus/send.py \\
        --channel standup --from alice --body "Shipped the README."
    python scripts/bus/send.py \\
        --channel standup --from alice --to bob \\
        --body "Can you review?"
    python scripts/bus/send.py \\
        --channel standup --from alice --body "Done." \\
        --ttl 24
"""

import argparse
import datetime
import fcntl
import json
import os
import sys


def week_key() -> str:
    """Return the current ISO week key (e.g. '2026-W15')."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%G-W%V")


def main() -> None:
    """Parse arguments and send a message."""
    parser = argparse.ArgumentParser(
        description="Send a message to an agent-bus channel"
    )
    parser.add_argument(
        "--channel", required=True, help="Channel name"
    )
    parser.add_argument(
        "--from", dest="sender", required=True,
        help="Sender agent ID"
    )
    parser.add_argument(
        "--to", default="all",
        help="Recipient agent ID or 'all' (default: all)"
    )
    parser.add_argument(
        "--body", required=True, help="Message body"
    )
    parser.add_argument(
        "--ttl", type=int, default=168,
        help="TTL in hours (default: 168)"
    )
    parser.add_argument(
        "--bus", default="system/bus",
        help="Bus root directory (default: system/bus)"
    )
    args = parser.parse_args()

    week = week_key()
    channel_dir = os.path.join(args.bus, "channels", args.channel)
    log_file = os.path.join(channel_dir, f"{week}.jsonl")

    if not os.path.isdir(channel_dir):
        print(
            f"Error: channel '{args.channel}' does not exist "
            f"at {channel_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y%m%dT%H%M%S%f") + "Z"
    msg_id = f"{args.sender}_{timestamp}"

    if args.to == "all":
        to = ["all"]
    else:
        to = [t.strip() for t in args.to.split(",")]

    msg = {
        "schema_version": 1,
        "id": msg_id,
        "channel": args.channel,
        "type": "msg",
        "from": args.sender,
        "to": to,
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "ttl_hours": args.ttl,
        "body": args.body,
    }

    if not os.path.exists(log_file):
        open(log_file, "w").close()

    with open(log_file, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(msg) + "\n")
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)

    print(f"Sent: {msg_id} -> {args.channel}")


if __name__ == "__main__":
    main()
