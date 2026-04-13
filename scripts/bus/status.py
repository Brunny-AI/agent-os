#!/usr/bin/env python3
"""Show bus health: channels, message counts, agent read positions.

Displays per-channel message counts, agent read receipts, and
calculates lag (how many messages each agent is behind).

Usage:
    python scripts/bus/status.py
    python scripts/bus/status.py --bus system/bus
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone


def week_key() -> str:
    """Return the current ISO week key (e.g. '2026-W15')."""
    return datetime.now(timezone.utc).strftime("%G-W%V")


def main() -> None:
    """Parse arguments and display bus status."""
    parser = argparse.ArgumentParser(
        description="Show agent-bus health"
    )
    parser.add_argument(
        "--bus", default="system/bus",
        help="Bus root directory (default: system/bus)"
    )
    args = parser.parse_args()

    week = week_key()
    channels_dir = os.path.join(args.bus, "channels")
    receipts_dir = os.path.join(args.bus, "receipts")

    print(f"=== agent-bus status  (week {week}) ===\n")

    channel_counts: dict[str, dict[str, int]] = {}
    print("CHANNELS")
    if not os.path.isdir(channels_dir):
        print("  (no channels directory found)")
    else:
        for channel in sorted(os.listdir(channels_dir)):
            if channel == "index.jsonl":
                continue
            channel_dir = os.path.join(channels_dir, channel)
            if not os.path.isdir(channel_dir):
                continue
            channel_counts[channel] = {}
            for f_name in os.listdir(channel_dir):
                if f_name.endswith(".jsonl"):
                    wk = f_name.replace(".jsonl", "")
                    fpath = os.path.join(channel_dir, f_name)
                    with open(fpath) as f:
                        count = sum(
                            1 for line in f if line.strip()
                        )
                    channel_counts[channel][wk] = count
            count = channel_counts[channel].get(week, 0)
            manifest_path = os.path.join(
                channel_dir, "manifest.json"
            )
            ctype = "?"
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    ctype = json.load(f).get("type", "?")
            print(
                f"  {channel}  [{ctype}]  "
                f"{count} messages this week"
            )

    agents: dict[str, dict[str, dict[str, int]]] = {}
    print("\nREAD RECEIPTS")
    if not os.path.isdir(receipts_dir):
        print("  (no receipts found)")
    else:
        for receipt_file in sorted(os.listdir(receipts_dir)):
            if not receipt_file.endswith(".json"):
                continue
            fpath = os.path.join(receipts_dir, receipt_file)
            with open(fpath) as f:
                receipt = json.load(f)
            agent = receipt.get(
                "agent", receipt_file.replace(".json", "")
            )
            updated = receipt.get("updated", "unknown")
            agent_offsets = receipt.get("offsets", {})
            agents[agent] = agent_offsets
            print(f"  {agent}  (updated {updated})")
            for ch, weeks in agent_offsets.items():
                for wk, pos in weeks.items():
                    print(f"    {ch}/{wk}: offset {pos}")

    if agents and channel_counts:
        print("\nLAG")
        all_channels = sorted(channel_counts.keys())
        for agent, agent_offsets in sorted(agents.items()):
            behind_total = 0
            lines = []
            for ch in all_channels:
                for wk, total in sorted(
                    channel_counts[ch].items()
                ):
                    pos = agent_offsets.get(ch, {}).get(wk, 0)
                    lag = max(0, total - pos)
                    if lag > 0:
                        lines.append(
                            f"    {ch}/{wk}: "
                            f"{pos}/{total} ({lag} behind)"
                        )
                        behind_total += lag
            if behind_total == 0:
                print(f"  {agent}: current")
            else:
                print(
                    f"  {agent}: "
                    f"{behind_total} message(s) behind"
                )
                for line in lines:
                    print(line)


if __name__ == "__main__":
    main()
