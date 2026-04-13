# Agent OS

Configurable framework for running multi-agent Claude Code
teams. Operational philosophy included.

**Zero dependencies.** Python 3.10+ and Bash. No databases,
no message queues, no cloud services.

## Quick Start

```bash
git clone https://github.com/Brunny-AI/agent-os.git
cd agent-os
python3 setup.py init
```

That's it. You now have a working 3-agent team:
- **coordinator** (operations)
- **builder-1** (engineering)
- **builder-2** (engineering)

### Customize your team

Edit `config/agent-os.yaml` to change team composition:

```yaml
team:
  name: "my-team"
  agents:
    - name: "lead"
      role: "coordinator"
    - name: "frontend"
      role: "builder"
    - name: "backend"
      role: "builder"
    - name: "qa"
      role: "reviewer"
```

Then re-run `python3 setup.py init`.

### Verify your setup

```bash
python3 setup.py validate
python3 setup.py status
```

## What Problems Does This Solve?

Agent OS is the system we built to run 4 AI agents 24/7
building a real company. It solves the problems nobody
talks about:

| Problem | Solution | Script |
|---------|----------|--------|
| Agents coast when you stop watching | Output clock detects idle agents in real-time | `scripts/monitor/output_clock.py` |
| Context degrades after hours | Shift boundaries with retros and fresh restarts | `scripts/cron/shift_refresh.sh` |
| No proof of work | Task engine with finish-to-start invariant | `scripts/task/engine.py` |
| Agents run out of ideas | Dual-loop ideation after every task completion | Built into task engine |
| Silent failures | Heartbeat-based liveness monitoring | `scripts/cron/manager.py` |
| Coordination overhead | File-based event bus with at-least-once delivery | `scripts/bus/*.py` |

## Architecture

```
agent-os/
  defaults/           # Shipped defaults (read-only)
    agent-os.yaml      # Default configuration
  config/              # User overrides (gitignored)
    agent-os.yaml      # Your customizations
    registry.yaml      # Agent registry (generated)
  scripts/
    bus/               # Event bus (messaging)
    cron/              # Cron manager (scheduling)
    task/              # Task engine (work tracking)
    monitor/           # Output clock (idle detection)
    config/            # Config loader
    hooks/             # Git hooks (privacy, workflow)
  system/              # Runtime state (gitignored)
    bus/               # Bus channels and receipts
    cron-registry.json # Heartbeat registry
    cache/             # Output clock state
  workspaces/          # Agent workspaces (gitignored)
    {agent}/           # Per-agent state
      profile.md       # Agent identity
      logs/            # Activity, progress, shift logs
      memory/          # Persistent memory
      scratch/         # Working files
  setup.py             # One-command bootstrapper
```

## Components

### Event Bus (`scripts/bus/`)

File-based messaging. JSONL logs, ISO week partitioning,
peek/commit delivery, flock concurrency protection.

```bash
# Send a message
python3 scripts/bus/send.py \
    --channel standup --from alice \
    --body "Shipped it." --bus system/bus

# Read new messages
python3 scripts/bus/read.py --agent bob \
    --bus system/bus --update
```

### Cron Manager (`scripts/cron/`)

Heartbeat registry for cross-agent liveness monitoring.

```bash
# Register and heartbeat
python3 scripts/cron/manager.py register alice poll JOB1
python3 scripts/cron/manager.py heartbeat alice poll

# Check who's alive
python3 scripts/cron/manager.py status
```

### Task Engine (`scripts/task/`)

Finish-to-start enforcer. You can't mark a task complete
unless you've already claimed the next one and produced
its first artifact.

```bash
# Claim, work, complete
python3 scripts/task/engine.py --agent alice --claim T-001
python3 scripts/task/engine.py --agent alice --artifact T-001 output.py
python3 scripts/task/engine.py --agent alice --claim T-002
python3 scripts/task/engine.py --agent alice --artifact T-002 spec.md
python3 scripts/task/engine.py --agent alice --complete T-001
```

### Output Clock (`scripts/monitor/`)

Filesystem-based idle detection. Four status levels:

| Status | Meaning |
|--------|---------|
| BUILDING | Git commits in window (shipped work) |
| WORKING | File modifications but no commits |
| STALE | Same files for 3+ polls (gaming) |
| IDLE | No output at all |

```bash
python3 scripts/monitor/output_clock.py --all --json
```

### Meeting System (`defaults/meetings/`)

Round-based discussion templates for 6 meeting types:
standup, general, postmortem, retro, brainstorm, 1:1.

Every meeting follows: pre-read, R1 positions (50 words),
R2 mandatory challenge (75 words), facilitator synthesis.

See `defaults/meetings/README.md` for the full protocol.

### Config (`scripts/config/`)

Override-based configuration. Defaults ship with the repo.
Users only specify what they want to change.

```bash
python3 scripts/config/loader.py --validate
python3 scripts/config/loader.py --key tasks.lease_minutes
```

## Design Principles

1. **Zero dependencies.** Everything runs with Python
   stdlib and Bash. No pip install. No Docker.

2. **Override, don't fork.** Customize via `config/`,
   never edit `defaults/` or `scripts/`.

3. **Files are the database.** JSON, JSONL, YAML.
   No SQLite, no Redis, no Postgres.

4. **Philosophy as defaults.** Anti-coasting, idle
   detection, shift boundaries are on by default.
   Turn them off if you want, but you won't want to.

5. **The repo IS the runtime.** No separate deploy.
   Clone it, run it, that's your production system.

## Requirements

- Python 3.10+
- Bash (Unix/macOS)
- Claude Code (for running agents)
- Git (for commit attribution)

## Configuration Reference

See `defaults/agent-os.yaml` for all available options.
Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `tasks.lease_minutes` | 15 | Task lease before expiration |
| `shifts.duration_hours` | 4 | Shift length before refresh |
| `monitoring.stale_threshold_polls` | 3 | Polls before STALE |
| `cron.poll_timeout_minutes` | 15 | Heartbeat timeout |
| `bus.default_ttl_hours` | 168 | Message TTL (1 week) |

## License

[MIT](LICENSE)

## Contributing

All changes go through pull requests. Privacy scan
required before every push (pre-push hook installed
by `setup.py init`).

See `.claude/rules/pr-workflow.md` for the full process.
