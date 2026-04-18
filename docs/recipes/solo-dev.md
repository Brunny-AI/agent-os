# Recipe: Solo Developer

You're one person building a side project. You open
Claude Code to work on it an hour a day — evenings and
weekends. You want an agent that maintains continuity
between sessions, picks up where you left off, and
flags when it's been drifting.

This recipe scales agent-os down to a single agent and
disables the team-coordination bits you don't need.

## Team shape

One agent. No coordinator, no peer reviewer, no event
bus traffic beyond self-messages. The agent plays both
builder and reviewer, but structurally logs its own
work so drift is visible when you open the repo.

## Configuration

Edit `config/agent-os.yaml`:

```yaml
team:
  name: "solo"
  agents:
    - name: "me"
      role: "builder"
```

Then:

```bash
python3 setup.py init
```

That's the whole team. Running `setup.py status` shows
one agent registered.

## What turns on

- **Task engine.** You still benefit from the
  finish-to-start invariant: you can't mark a task
  COMPLETE until you've claimed the next one and
  produced its first artifact. Keeps scope honest
  even when you're the only reader.
- **Output clock.** Visible whenever you run
  `python3 scripts/monitor/output_clock.py --all`. On
  a solo project, this tells you in one glance
  whether you actually produced files this session
  or just thought about the code.
- **Shift refresh.** After 4 hours, the agent prompts
  a context refresh. Useful for multi-evening work
  where the session is long enough to degrade.
- **Active-task gate.** Blocks the heartbeat if your
  active task has no recent artifact — surfaces
  "I've been reading, not writing" state structurally.

## What stays off

- **Meeting system.** No peers to meet with. The
  templates in `defaults/meetings/` are ignored.
- **Event bus.** Runs locally but carries only
  self-messages (useful if you want to leave
  yourself notes; silent otherwise).
- **Mutual-unblock / CO-review rules.** Single-author
  repos don't need them. No branch protection
  required.

## Daily workflow

A typical session:

```bash
# Start Claude Code pointed at this repo.

python3 scripts/task/engine.py --agent me --status
# See what you were working on.

python3 scripts/task/engine.py --agent me --claim \
    T-042 --claim-desc "Add pagination to list view" \
    --claim-first-step "Read current list logic"

# ... you code ...

python3 scripts/task/engine.py --agent me --artifact \
    T-042 src/list.py
```

When you close Claude Code, the task stays
IN_PROGRESS with a lease. Tomorrow you resume the
same task without re-asking yourself "wait, what was
I doing?"

## When to graduate to a bigger team

Stay solo until these hurt:

- You're reviewing your own code and missing things
  a fresh reader would catch → add a second agent
  as reviewer.
- You're doing GTM / content alongside build → split
  off a second agent for writing, distribution,
  metrics.
- The project gets real users and you have more
  work than evening hours → multi-agent for
  parallel lanes (see `docs/recipes/team-mirror.md`
  once that lands).

The recipe is deliberately small. If agent-os is
doing its job, solo mode should feel like a more
structured version of your current workflow — not a
second job.
