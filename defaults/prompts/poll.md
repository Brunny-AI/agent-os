# Poll Prompt Template

Use this prompt with CronCreate to set up agent polling.
Replace `{agent}` with the agent name and `{root}` with
the repo root path.

## Prompt

```
You are {agent}. Silent poll -- output ONLY if action needed.
Working dir: {root}.

1. Bus: Read new messages.
   python3 scripts/bus/read.py --agent {agent} \
     --bus system/bus \
     --offsets workspaces/{agent}/memory/bus-offsets.json \
     --peek
   If new messages: reply to each, then --update to commit.

2. Output clock: Check all agents.
   python3 scripts/monitor/output_clock.py --all --json
   If any agent IDLE: investigate and help unblock.

3. Task engine: Check leases.
   python3 scripts/task/engine.py --agent {agent} --check-lease
   python3 scripts/task/engine.py --agent {agent} --status
   If expired: claim a new task immediately.

4. Heartbeat:
   python3 scripts/cron/manager.py heartbeat {agent} poll

Rules:
- NO output if nothing needs attention.
- If idle: start working immediately.
- If teammate idle: help them unblock.
```

## Setup

```bash
# Register the poll cron (every 5 minutes)
python3 scripts/cron/manager.py register {agent} poll {JOB_ID}
```

## Customization

Adjust the poll prompt to match your team's workflow:
- Add standup checks (hourly meeting channel scan)
- Add shift boundary detection (4h context refresh)
- Add custom monitoring (build status, deploy checks)

The poll prompt is the heartbeat of the agent OS. It runs
every 5 minutes and keeps agents coordinated, productive,
and aware of each other's state.
