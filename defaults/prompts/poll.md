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

3a. Active-task + parallel-work gate (HARD BLOCK on heartbeat).
    gate="$(python3 scripts/task/engine.py --agent {agent} \
      --json-status \
      | python3 scripts/cron/poll_gates.py \
      --max-age-min 15 --blocked-grace-min 15)"
    case "$gate" in
      OK) ;;  # Active task with artifact <15min — proceed
      ACTIVE-TASK-REQUIRED|STALE-ARTIFACT)
        # Heartbeat is BLOCKED. Claim + produce an artifact:
        # 1. Pick a task (assigned to you, or unassigned).
        # 2. python3 scripts/task/engine.py --agent {agent} \
        #      --claim TASK_ID
        # 3. Write a real file (code, spec, doc — anything
        #    concrete; touching files to game the gate
        #    defeats the point).
        # 4. python3 scripts/task/engine.py --agent {agent} \
        #      --artifact TASK_ID path/to/file
        # 5. Re-run this gate; only proceed when OK.
        ;;
      PARALLEL-TASK-REQUIRED)
        # Solo IN_PROGRESS + a blocked task >15min old.
        # Pull a SECOND independent task in an orthogonal
        # lane and produce its first artifact, then proceed.
        # Blocked-on-upstream is real, but the agent doesn't
        # have to be idle during it.
        ;;
    esac

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
