#!/usr/bin/env python3
"""Aggregate gate JSONL log into a daily summary.

Reads the JSONL file that poll_gates.py writes when run
with --log-file. Emits per-token counts, per-agent
counts, and the most recent STALE-ARTIFACT events. Used
to answer the "how often does the gate catch real
drift?" question with data rather than vibes.

Stdlib only — same constraints as the gate itself.

Usage:
    python3 scripts/monitor/gate_audit.py \\
      --log-file system/gate-audit.jsonl --days 1

    python3 scripts/monitor/gate_audit.py \\
      --log-file system/gate-audit.jsonl --days 7 \\
      --json  # machine-readable

Exit: 0 on success, 1 on read/parse errors.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import sys
import typing


def _parse_iso(ts: str) -> datetime.datetime | None:
    """Parse a Zulu-or-offset ISO 8601 string or None."""
    try:
        return datetime.datetime.fromisoformat(
            ts.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def _summarize(
    entries: list[dict[str, typing.Any]],
) -> dict[str, typing.Any]:
    """Reduce filtered log entries to a summary dict.

    Args:
        entries: JSONL records already filtered to the
            window of interest.

    Returns:
        Dict with keys `total`, `by_token` (Counter as
        dict), `by_agent` (nested dict), `stale_events`
        (recent STALE-ARTIFACT entries, oldest first,
        capped at 20), and `window_start`/`window_end`.
    """
    by_token: collections.Counter = collections.Counter()
    by_agent: dict[
        str, collections.Counter
    ] = collections.defaultdict(collections.Counter)
    stale_events: list[dict[str, typing.Any]] = []
    tss: list[str] = []
    for entry in entries:
        token = entry.get("token", "UNKNOWN")
        agent = entry.get("agent", "unknown")
        by_token[token] += 1
        by_agent[agent][token] += 1
        tss.append(entry.get("ts", ""))
        if token == "STALE-ARTIFACT":
            stale_events.append({
                "ts": entry.get("ts"),
                "agent": agent,
                "task": entry.get("freshest_task"),
                "age_min": entry.get("freshest_age_min"),
            })
    return {
        "total": sum(by_token.values()),
        "by_token": dict(by_token),
        "by_agent": {
            agent: dict(counts)
            for agent, counts in sorted(by_agent.items())
        },
        "stale_events": stale_events[-20:],
        "window_start": min(tss) if tss else None,
        "window_end": max(tss) if tss else None,
    }


def _render_text(summary: dict[str, typing.Any], days: int) -> str:
    """Render summary as human-readable text."""
    lines = [
        f"Gate audit — last {days} day(s)",
        f"Window: {summary['window_start'] or 'n/a'} "
        f"→ {summary['window_end'] or 'n/a'}",
        f"Total invocations: {summary['total']}",
        "",
        "By token:",
    ]
    by_token = summary["by_token"]
    for token in sorted(
        by_token, key=lambda t: -by_token[t]
    ):
        lines.append(f"  {token}: {by_token[token]}")
    lines.append("")
    lines.append("By agent:")
    for agent, counts in summary["by_agent"].items():
        counts_str = ", ".join(
            f"{k}={v}" for k, v in sorted(counts.items())
        )
        lines.append(f"  {agent}: {counts_str}")
    stale = summary["stale_events"]
    if stale:
        lines.append("")
        lines.append(
            f"Recent STALE-ARTIFACT ({len(stale)} shown):"
        )
        for event in stale:
            lines.append(
                f"  {event['ts']} {event['agent']} "
                f"{event['task']} {event['age_min']}min"
            )
    return "\n".join(lines)


def main() -> None:
    """Read JSONL log, filter by window, emit summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-file", required=True,
        help="Path to JSONL log written by poll_gates.py",
    )
    parser.add_argument(
        "--days", type=int, default=1,
        help="Window size in days (default: 1)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit JSON instead of human-readable text",
    )
    args = parser.parse_args()

    path = pathlib.Path(args.log_file)
    if not path.exists():
        print(
            f"no log at {args.log_file}", file=sys.stderr
        )
        sys.exit(1)

    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=args.days)
    )

    entries: list[dict[str, typing.Any]] = []
    parse_failures = 0
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                parse_failures += 1
                continue
            ts = _parse_iso(entry.get("ts", ""))
            if ts is None or ts < cutoff:
                continue
            entries.append(entry)

    if parse_failures:
        # Docstring promises exit 1 on read/parse errors.
        # Silent skipping caused undercounting; warn to
        # stderr so the counts in summary remain trusted
        # while the operator knows to investigate.
        print(
            f"warning: {parse_failures} malformed JSONL "
            f"line(s) skipped",
            file=sys.stderr,
        )

    summary = _summarize(entries)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(_render_text(summary, args.days))


if __name__ == "__main__":
    main()
