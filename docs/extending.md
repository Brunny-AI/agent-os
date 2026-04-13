# Extending Agent OS

How to customize Agent OS without modifying core
scripts.

## Adding Agents

Edit `config/agent-os.yaml`:

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

Run `python3 setup.py init` to create workspaces
for new agents. Existing workspaces are not modified.

## Custom Poll Prompts

Each agent's poll prompt controls what it checks
every 5 minutes. The default template is in
`defaults/prompts/poll.md`.

To customize, create your own prompt and reference
it when creating the cron job:

```
CronCreate:
  cron: "7,12,17,22,27,32,37,42,47,52,57 * * * *"
  prompt: "<your custom poll prompt>"
```

The poll prompt should include:
1. Bus read (peek/commit pattern)
2. Output clock check (peer monitoring)
3. Task engine lease check
4. Heartbeat

## Custom Scheduled Tasks

Each agent can have an `agent-schedule.json` in their
workspace with recurring tasks:

```json
{
  "version": 1,
  "owner": "alice",
  "tasks": {
    "my_task": {
      "name": "My custom task",
      "type": "interval",
      "interval_minutes": 30,
      "command": "python3 my_script.py",
      "description": "What this does",
      "last_run": null,
      "execution_log": []
    }
  }
}
```

Three task types:
- **session_start**: Runs once per shift (e.g., daily
  feed generation)
- **interval**: Runs every N minutes (e.g., git
  commit, memory health check)
- **cadence**: Runs after N hours since last execution
  (e.g., content publishing gates)

## Adding Bus Channels

```bash
python3 scripts/bus/new_channel.py \
    --name my-channel \
    --owner alice \
    --type async \
    --bus system/bus
```

Channel types:
- **async**: Persistent communication (standup,
  urgent, project-specific)
- **meeting**: Temporary, round-based discussion
  with mandatory challenges

## Custom Git Hooks

Agent OS installs two git hooks:
- `pre-commit`: Blocks direct commits to main
- `pre-push`: Privacy scan for sensitive information

Add your own hooks in `scripts/hooks/` and update
`setup.py` to install them, or add them manually to
`.git/hooks/`.

## Workspace Layout

Each agent workspace follows this structure:

```
workspaces/{agent}/
  profile.md           # Identity and operating rules
  CLAUDE.md            # Session startup instructions
  logs/
    activity/          # What happened (append-only)
    progress/          # Current state (wiki)
      current-tasks.yaml
      session-handoff.md
      task-engine-state.json
    shift/             # Shift refresh logs
  memory/
    bus-offsets.json    # Read position per channel
    learnings.md       # Persistent knowledge
  scratch/
    agent-schedule.json  # Scheduled tasks
```

Files marked "append-only" should never be edited
after writing. Files marked "wiki" can be overwritten.

## Integration Points

### Claude Code

Agent OS is designed for Claude Code sessions.
Each agent runs in its own Claude Code process.
The poll and scheduler are Claude Code cron jobs
(`CronCreate`), not system crons.

### Git

Agents commit to the workspaces/ directory as proof
of work. The output clock checks git history to
determine BUILDING status. Each agent uses its own
git identity:

```bash
git -c user.name="{agent}" \
    -c user.email="{agent}@example.com" \
    commit -m "[{agent}] verb: description"
```

### File System

All state is in files. No external services. This
means Agent OS works anywhere you can run Python and
Claude Code -- local machine, CI runner, or cloud VM.

## What NOT to Modify

- `defaults/` -- shipped read-only defaults
- `scripts/` -- core OS scripts
- `docs/` -- documentation

Customize through `config/` overrides and workspace
files. If you find yourself editing core scripts, you
may need a feature that should be configurable. Open
an issue.
