# Scheduler Prompt Template

Hourly scheduler for recurring tasks. Replace `{agent}`
with the agent name and `{root}` with the repo root.

## Prompt

```
You are {agent}. Hourly scheduler.
Working dir: {root}.

1. Read schedule: workspaces/{agent}/scratch/agent-schedule.json
2. Get current UTC time.
3. For each task, check if due:
   - session_start: fires once per session
   - interval: fires when elapsed >= interval_minutes
4. Execute due tasks.
5. Update last_run in schedule JSON.
6. Heartbeat:
   python3 scripts/cron/manager.py heartbeat {agent} scheduler

Silent if nothing is due.
```

## Setup

```bash
# Register the scheduler cron (hourly)
python3 scripts/cron/manager.py register {agent} scheduler {JOB_ID}
```

## Schedule File Format

```json
{
  "version": 1,
  "owner": "{agent}",
  "tasks": {
    "my_task": {
      "name": "My recurring task",
      "type": "interval",
      "interval_minutes": 60,
      "command": "python3 scripts/my_script.py",
      "last_run": null,
      "execution_log": []
    }
  }
}
```
