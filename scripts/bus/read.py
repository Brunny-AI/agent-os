#!/usr/bin/env python3
"""Read new messages from all agent-bus channels.

Supports two modes for at-least-once delivery:
  --peek   Show new messages WITHOUT advancing offsets
  --update Advance offsets and write read receipt (commit)

Usage:
    python scripts/bus/read.py --agent alice
    python scripts/bus/read.py --agent alice --peek
    python scripts/bus/read.py --agent alice --update
    python scripts/bus/read.py --agent alice \\
        --offsets workspaces/alice/memory/bus-offsets.json
"""

from __future__ import annotations

import argparse
import fcntl
import glob
import json
import os
import sys
import tempfile
from datetime import datetime, timezone


def load_offsets(path: str) -> dict[str, object]:
    """Load offset state from disk, or return empty defaults.

    Returns empty defaults if the file is missing or corrupt.
    """
    if not os.path.exists(path):
        return {"schema_version": 1, "offsets": {}}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        print(
            f"Warning: corrupt offsets file {path}, "
            f"starting fresh",
            file=sys.stderr,
        )
        return {"schema_version": 1, "offsets": {}}


def save_offsets_locked(
    path: str,
    new_offsets: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    """Atomically merge offsets using max() under flock.

    Prevents stale writers from regressing another agent's
    read position. Uses a separate .lock file so the lock
    survives file rewrites.

    Args:
        path: Path to the bus-offsets.json file.
        new_offsets: Channel/week offset values to merge.

    Returns:
        The merged offset dict after max-merge.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({"schema_version": 1, "offsets": {}}, f)

    lock_path = path + ".lock"
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            with open(path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, ValueError):
            existing = {"schema_version": 1, "offsets": {}}
        merged = existing.get("offsets", {})
        for ch, weeks in new_offsets.items():
            if ch not in merged:
                merged[ch] = {}
            for wk, val in weeks.items():
                old = merged.get(ch, {}).get(wk, 0)
                merged[ch][wk] = max(old, val)
        existing["offsets"] = merged
        parent = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(dir=parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(existing, f, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
        fcntl.flock(lock_f, fcntl.LOCK_UN)
    return merged


def is_expired(msg: dict) -> bool:
    """Check if a message has exceeded its TTL."""
    try:
        ts = datetime.fromisoformat(
            msg["timestamp"].replace("Z", "+00:00")
        )
        ttl = msg.get("ttl_hours", 168)
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() > ttl * 3600
    except (KeyError, ValueError, TypeError):
        return False


def main() -> None:
    """Parse arguments and read bus messages."""
    parser = argparse.ArgumentParser(
        description="Read new messages from agent-bus channels"
    )
    parser.add_argument(
        "--agent", required=True, help="Your agent ID"
    )
    parser.add_argument(
        "--offsets",
        help="Path to bus-offsets.json "
        "(default: workspaces/{agent}/memory/bus-offsets.json)"
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Update offsets after reading (commit)"
    )
    parser.add_argument(
        "--peek", action="store_true",
        help="Show new messages WITHOUT advancing offsets"
    )
    parser.add_argument(
        "--bus", default="system/bus",
        help="Bus root directory (default: system/bus)"
    )
    parser.add_argument(
        "--channel",
        help="Read only this channel (default: all)"
    )
    args = parser.parse_args()

    if args.peek and args.update:
        print(
            "Error: --peek and --update are mutually exclusive.",
            file=sys.stderr,
        )
        sys.exit(1)

    offsets_path = (
        args.offsets
        or f"workspaces/{args.agent}/memory/bus-offsets.json"
    )
    offsets_data = load_offsets(offsets_path)
    offsets = offsets_data.get("offsets", {})

    channels_dir = os.path.join(args.bus, "channels")
    if not os.path.isdir(channels_dir):
        print(
            f"Error: bus channels directory not found "
            f"at {channels_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    new_offsets = {k: dict(v) for k, v in offsets.items()}
    total_new = 0

    if args.channel:
        channel_list = [args.channel]
    else:
        channel_list = sorted(os.listdir(channels_dir))

    for channel in channel_list:
        channel_dir = os.path.join(channels_dir, channel)
        if not os.path.isdir(channel_dir):
            continue

        log_files = sorted(
            glob.glob(os.path.join(channel_dir, "????-W??.jsonl"))
        )
        if not log_files:
            continue

        channel_offsets = offsets.get(channel, {})

        for log_file in log_files:
            week = os.path.basename(log_file)[:-6]
            current_offset = channel_offsets.get(week, 0)

            with open(log_file) as f:
                lines = f.readlines()

            new_lines = lines[current_offset:]
            if not new_lines:
                continue

            safe_offset = current_offset
            last_idx = len(new_lines) - 1
            for i, line in enumerate(new_lines):
                line = line.strip()
                if not line:
                    safe_offset = current_offset + i + 1
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    if i == last_idx:
                        # Last line may be a partial write
                        # from a concurrent sender. Stop here
                        # so it can be retried next read.
                        break
                    print(
                        f"  [PARSE ERROR in "
                        f"{channel}/{week} line "
                        f"{current_offset + i + 1}, skipped]",
                        file=sys.stderr,
                    )
                    safe_offset = current_offset + i + 1
                    continue

                if not isinstance(msg, dict):
                    safe_offset = current_offset + i + 1
                    continue

                safe_offset = current_offset + i + 1

                if is_expired(msg):
                    continue

                if msg.get("from") == args.agent:
                    continue

                raw_to = msg.get("to", ["all"])
                if not isinstance(raw_to, list):
                    raw_to = [str(raw_to)]
                to: list[str] = []
                for t in raw_to:
                    to.extend(str(t).split(","))
                to = [t.strip() for t in to]
                if "all" not in to and args.agent not in to:
                    continue

                sender = msg.get("from", "?")
                ts = msg.get("timestamp", "?")
                body = msg.get("body", "")
                print(
                    f"[{channel}] {sender} -> "
                    f"{', '.join(to)}  ({ts})"
                )
                print(f"  {body}")
                print()
                total_new += 1

            if channel not in new_offsets:
                new_offsets[channel] = {}
            new_offsets[channel][week] = safe_offset

    if total_new == 0:
        print("No new messages.")

    if args.peek:
        print(
            f"Peeked {total_new} message(s). "
            f"Offsets NOT advanced (use --update to commit)."
        )
    elif args.update:
        merged = save_offsets_locked(offsets_path, new_offsets)
        print(f"Offsets updated: {offsets_path}")

        receipt_dir = os.path.join(args.bus, "receipts")
        os.makedirs(receipt_dir, exist_ok=True)
        receipt_path = os.path.join(
            receipt_dir, f"{args.agent}.json"
        )
        receipt = {
            "schema_version": 1,
            "agent": args.agent,
            "updated": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "offsets": merged,
        }
        fd, tmp = tempfile.mkstemp(dir=receipt_dir)
        try:
            with os.fdopen(fd, "w") as rf:
                json.dump(receipt, rf, indent=2)
                rf.write("\n")
                rf.flush()
                os.fsync(rf.fileno())
            os.replace(tmp, receipt_path)
        except BaseException:
            os.unlink(tmp)
            raise
        print(f"Read receipt updated: {receipt_path}")


if __name__ == "__main__":
    main()
