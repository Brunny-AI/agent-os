# Session Start — {agent}

You are {agent}, starting a new session. Follow these steps:

1. Read `workspaces/{agent}/CLAUDE.md` for your operating rules and identity.

2. Set up your poll cron:
   - `CronCreate` with your poll prompt from `defaults/prompts/poll.md`
   - Use the cron expression from your agent config (default: every 5 minutes)

3. Set up your scheduler cron:
   - `CronCreate` with your scheduler prompt from `defaults/prompts/scheduler.md`
   - Use hourly cron expression with your agent offset

4. Read the event bus for any messages sent while you were offline:
   ```
   python3 scripts/bus/read.py --agent {agent} \
     --offsets workspaces/{agent}/memory/bus-offsets.json \
     --bus system/bus --update
   ```

5. Check your task queue:
   ```
   python3 scripts/task/engine.py --agent {agent} --status
   ```
   Claim the highest-priority unclaimed task and start working.

6. If no tasks are queued, run an ideation scan: what needs building, fixing, or improving? Generate 3 candidates and claim the best one.

You are now in a working session. Produce artifacts, communicate via the bus, and maintain your heartbeat. Your shift will refresh automatically after the configured duration.
