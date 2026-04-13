# Event Bus

File-based messaging system for inter-agent communication.
No external dependencies -- uses only Python stdlib.

## Quick Start

```bash
# Create the bus directory structure
mkdir -p system/bus/channels

# Create a channel
python3 scripts/bus/new_channel.py \
    --name general --owner alice --bus system/bus

# Send a message
python3 scripts/bus/send.py \
    --channel general --from alice \
    --body "Hello team" --bus system/bus

# Send a directed message
python3 scripts/bus/send.py \
    --channel general --from alice --to bob \
    --body "Can you review?" --bus system/bus

# Read messages (peek without advancing offsets)
python3 scripts/bus/read.py \
    --agent bob --bus system/bus --peek

# Read and commit (advance offsets)
python3 scripts/bus/read.py \
    --agent bob --bus system/bus --update

# Check bus health
python3 scripts/bus/status.py --bus system/bus

# Rotate weekly logs
python3 scripts/bus/snapshot.py \
    --from coordinator --bus system/bus
```

## Scripts

| Script | Purpose |
|--------|---------|
| `send.py` | Send a message to a channel |
| `read.py` | Read new messages (peek/commit) |
| `new_channel.py` | Create a channel |
| `status.py` | Show bus health and lag |
| `snapshot.py` | Close current week, open next |

## Design

- **Storage**: JSONL files, one per channel per ISO week
- **Delivery**: At-least-once via peek/commit pattern
- **Concurrency**: flock-based offset locking (Unix)
- **Rotation**: ISO week partitions, snapshot-based
- **Addressing**: broadcast (`all`) or directed (`--to`)

## Directory Layout

```
system/bus/
  channels/
    index.jsonl          # channel index
    {channel}/
      manifest.json      # channel metadata
      2026-W15.jsonl     # messages for ISO week 15
      2026-W16.jsonl     # messages for ISO week 16
  receipts/
    {agent}.json         # per-agent read receipt
```
