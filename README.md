# Agent OS

[![CI](https://github.com/Brunny-AI/agent-os/actions/workflows/ci.yml/badge.svg)](https://github.com/Brunny-AI/agent-os/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#requirements)

Configurable framework for running multi-agent Claude Code
teams. Operational philosophy included.

**Zero dependencies.** Python 3.10+ and Bash. No databases,
no message queues, no cloud services. The test suite runs on a
fresh clone before you've installed anything.

## Quick Start

```bash
git clone https://github.com/Brunny-AI/agent-os.git
cd agent-os
python3 setup.py init
bash examples/quickstart/run-demo.sh  # ~5s end-to-end smoke, 7 MVP components
python3 setup.py validate             # confirms setup is green
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

### See it run end-to-end (~5 seconds)

```bash
bash examples/quickstart/run-demo.sh
```

You'll see all 7 MVP components run end-to-end: task engine,
event bus, cron manager, output clock, active-task gate, etc.

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

## How this differs from CrewAI / AutoGen / LangGraph

Those frameworks optimize for **orchestrating LLM calls** to
answer a user query — fan out, reduce, return.

Agent OS optimizes for **keeping agents productive across
weeks**. The failure modes are operational (coasting, context
degradation, stuck-in-blocked states) not reasoning failures.
Different problem, different stack. Use both if your agents
both respond to queries AND run long-lived — Agent OS handles
the liveness surface.

## Operational docs we use ourselves

What we actually run on top of agent-os, with the artifacts
to back the multi-agent claims (live run-evidence pending):

- **Operational guardrails** — the 6 checks before you leave
  an agent running overnight, distilled from a month of
  running this in production:
  [`docs/operational-guardrails.md`](docs/operational-guardrails.md)
- **Compliance log template** — battle-tested §1-6 structure
  (formation, work-log, exclusions, isolation, expenses,
  evidence-vault) for any small org running multi-agent ops:
  [`examples/compliance-log/template.md`](examples/compliance-log/template.md)

## Recipes

Worked examples for specific team shapes. Each recipe is a
self-contained walkthrough: the config, what turns on, what
stays off, and when to graduate to something bigger.

- **Solo developer** — one agent, continuity between evening
  sessions, drift visible:
  [`docs/recipes/solo-dev.md`](docs/recipes/solo-dev.md)

More recipes land as we learn what users actually reach for
(4-agent team mirror, code-review bot, OSS-triage bot).
External contributions welcome — see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

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

### Autonomous Mode (`scripts/cron/agent_loop.sh`)

Runs an agent in a loop with automatic shift refresh.
No human needed for restarts.

```bash
# Start an agent in autonomous mode
bash scripts/cron/agent_loop.sh builder-1

# Or run in a detached screen session
screen -dmS builder-1 bash scripts/cron/agent_loop.sh builder-1
```

The wrapper:
- Starts Claude with a session-start prompt (shift 1)
  or session-refresh prompt (shift 2+)
- Spawns a sidecar that watches for a shift-refresh
  flag file
- When the agent writes the flag (via `shift_refresh.sh`),
  the sidecar kills Claude and the wrapper restarts
- Detects crash loops (3 rapid exits) and stops with
  an alert

### Watchdog (`scripts/monitor/watchdog.sh`)

External monitoring for agent liveness. Run via
launchd or system cron every 5 minutes.

```bash
# Check all agents, alert via macOS notification
bash scripts/monitor/watchdog.sh --notify

# Check + push notification via ntfy.sh
bash scripts/monitor/watchdog.sh --ntfy my-topic
```

If an agent's heartbeat is expired, the watchdog
tries auto-recovery (restart in screen/tmux) and
sends alerts to the bus and optionally to your phone.

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
| `autonomous.grace_period_seconds` | 5 | Sidecar kill delay |
| `autonomous.crash_loop_threshold` | 3 | Rapid exits before stop |

## License

[MIT](LICENSE)

## Contributing

All changes go through pull requests. Privacy scan
required before every push (pre-push hook installed
by `setup.py init`).

See `.claude/rules/pr-workflow.md` for the full process.
