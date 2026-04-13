# Session Refresh — {agent}

You are {agent}, resuming after a shift refresh. This is NOT a new session — you are continuing your work with fresh context.

1. Read `workspaces/{agent}/CLAUDE.md` for your operating rules.

2. Read your handoff file at `workspaces/{agent}/logs/progress/session-handoff.md`:
   - This tells you what you were working on and where you left off.
   - If missing, fall back to your task queue and recent bus messages.

3. Restore your crons (they died with the old process):
   - Poll cron: `CronCreate` with prompt from `defaults/prompts/poll.md`
   - Scheduler cron: `CronCreate` with prompt from `defaults/prompts/scheduler.md`

4. Read new bus messages (only unread, from saved offsets):
   ```
   python3 scripts/bus/read.py --agent {agent} \
     --offsets workspaces/{agent}/memory/bus-offsets.json \
     --bus system/bus --update
   ```

5. Resume the task from the handoff immediately. No deep startup, no full re-read. You are picking up where you left off.
