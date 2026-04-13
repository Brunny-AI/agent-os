# Session Refresh — {agent}

You are {agent}, resuming after a shift refresh. This is
NOT a new session. You are continuing your work with
fresh context.

## 1. Read your handoff

Check `workspaces/{agent}/logs/progress/session-handoff.md`.
This tells you:
- What you were working on
- Where you left off (file, line, next step)
- What's next in your queue

If the handoff is missing, fall back to:
- `python3 scripts/task/engine.py --agent {agent} --status`
- Recent bus messages (step 3 below)
- `git log --author="{agent}" --since="6 hours ago"`

## 2. Restore coordination infrastructure

Your crons died with the old process. Recreate them:

Poll cron (every 5 minutes):
- Read `defaults/prompts/poll.md`, replace `{agent}`
- `CronCreate` with your cron expression
- Register: `python3 scripts/cron/manager.py register {agent} poll <job_id>`

Scheduler cron (hourly):
- Read `defaults/prompts/scheduler.md`, replace `{agent}`
- `CronCreate` with hourly expression
- Register: `python3 scripts/cron/manager.py register {agent} scheduler <job_id>`

Verify both crons exist: `CronList` must show 2+ jobs.

## 3. Check for messages during refresh

Teammates may have sent messages while you restarted:

```
python3 scripts/bus/read.py --agent {agent} \
  --offsets workspaces/{agent}/memory/bus-offsets.json \
  --bus system/bus --update
```

Reply to anything addressed to you.

## 4. Resume immediately

Pick up the task from your handoff. No deep startup,
no full re-read of all files. You already know who you
are. Get back to producing artifacts.

If your previous task is complete, claim the next one
from the handoff's priority list or your task queue.
