# Quickstart Example

A minimal 3-agent team that demonstrates all Agent OS
components working together.

## Setup

```bash
# From the repo root
python3 setup.py init
```

This creates:
- **coordinator** - Operations agent (manages schedule)
- **builder-1** - Engineering agent
- **builder-2** - Engineering agent

## Running Agents

Each agent runs in its own Claude Code session:

```bash
# Terminal 1: Start coordinator
claude --profile coordinator

# Terminal 2: Start builder-1
claude --profile builder-1

# Terminal 3: Start builder-2
claude --profile builder-2
```

## What Happens

1. Each agent reads their `workspaces/{name}/CLAUDE.md`
2. They register their poll cron with the cron manager
3. Every 5 minutes, each agent:
   - Reads bus messages and responds
   - Checks peer output clocks for idle agents
   - Checks task engine for expired leases
   - Sends heartbeat
4. Every 4 hours, agents refresh their context
5. Tasks flow through the finish-to-start engine

## Observing

```bash
# See who's alive
python3 scripts/cron/manager.py status

# See what's being produced
python3 scripts/monitor/output_clock.py --all --json

# See task states
python3 scripts/task/engine.py --agent coordinator --status

# Read bus messages
python3 scripts/bus/status.py --bus system/bus
```

## Customizing

Edit `config/agent-os.yaml` to:
- Change team size or agent names
- Adjust shift duration (default: 4 hours)
- Tune task lease time (default: 15 minutes)
- Modify output clock sensitivity
