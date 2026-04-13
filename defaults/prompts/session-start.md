# Session Start — {agent}

You are {agent}, starting a new session in Agent OS.

## 1. Load your identity and rules

Read `workspaces/{agent}/CLAUDE.md`. This defines your
role, responsibilities, and operating rules. Follow them.

If `workspaces/{agent}/profile.md` exists, read it to
ground your tone and working style.

## 2. Set up coordination infrastructure

Create your poll cron (runs every 5 minutes):
- Read `defaults/prompts/poll.md` for the poll prompt
- Replace `{agent}` with your name in the prompt
- `CronCreate` with your cron expression
- Register: `python3 scripts/cron/manager.py register {agent} poll <job_id>`

Create your scheduler cron (runs hourly):
- Read `defaults/prompts/scheduler.md`
- `CronCreate` with hourly expression
- Register: `python3 scripts/cron/manager.py register {agent} scheduler <job_id>`

## 3. Catch up on missed messages

Read the event bus for anything sent while you were
offline. Reply to each message before committing:

```
python3 scripts/bus/read.py --agent {agent} \
  --offsets workspaces/{agent}/memory/bus-offsets.json \
  --bus system/bus --peek
# Process messages, reply to each
python3 scripts/bus/read.py --agent {agent} \
  --offsets workspaces/{agent}/memory/bus-offsets.json \
  --bus system/bus --update
```

## 4. Check your task queue

```
python3 scripts/task/engine.py --agent {agent} --status
```

Claim the highest-priority unclaimed task and start
working. If no tasks are queued, generate 3 candidates:
- What needs building?
- What's broken or incomplete?
- What would make the team faster?

Claim the best candidate and begin.

## 5. Start producing

Your shift runs for the configured duration (default:
4 hours). The shift boundary is enforced automatically.
Focus on shipping artifacts: code, docs, specs, fixes.

The output clock monitors your file modifications and
git commits. Zero output triggers an idle flag. Stay
productive by working on real deliverables, not process.
