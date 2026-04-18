# Recipe: Solo Developer

You're one person building a side project. You open
Claude Code to work on it an hour a day — evenings and
weekends. You want an agent that maintains continuity
between sessions, picks up where you left off, and
flags when it's been drifting.

This recipe scales Agent OS to a single agent. Some
coordination components (meeting quorum, mutual-unblock
cross-repo reviews) naturally become no-ops because
they need multiple agents. Two others (checkout
approval, peer-review gate) would otherwise block a
solo author — two small config overrides below
redirect them to the sole agent so they stay active
without a teammate. The per-agent discipline (task
engine, output clock, shift refresh, active-task gate)
still applies exactly the same way.

## Team shape

One agent. The agent plays both builder and reviewer,
but structurally logs its own work so drift is visible
when you open the repo the next session.

## Configuration

Create `config/agent-os.yaml` (file does not exist on a
fresh install; it's the user override for `defaults/
agent-os.yaml`):

```yaml
team:
  name: "solo"
  agents:
    - name: "me"
      role: "builder"

# The default governance block assumes a multi-agent team
# and routes checkout approval through a "coordinator"
# agent that doesn't exist here. Override to the sole
# agent so the checkout flow has a valid approver.
governance:
  checkout_approver_agent: "me"

# Default workflow assumes a peer reviewer (min_reviewers: 2).
# With one agent, no peer exists — lower the reviewer count
# to 1 so workflow steps that read this config don't block
# on a missing peer. Matches precedent set by
# `examples/workflows/minimal.yaml`. (The prose at
# `defaults/rules/pr-workflow.md` still describes a multi-
# agent flow; in solo mode the min_reviewers: 1 value is the
# effective gate.)
workflow:
  min_reviewers: 1
```

Then:

```bash
python3 setup.py init
```

That's the whole team. Running `python3 setup.py status`
shows one agent registered.

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

## What's a no-op with one agent

These run but have nothing to do in solo mode:

- **Meeting system.** Meetings need a quorum of
  agents; with one agent there's no one to run
  round-based discussion with. Templates in
  `defaults/meetings/` are harmless leftovers.
- **Event bus.** Still runs (same JSONL machinery).
  Posts go to you. Useful as a notes channel; silent
  if unused.
- **GitHub peer-review gating.** Multi-agent repos
  typically configure branch-protection rules (CODEOWNERS,
  required reviewer count, required status checks) that
  presume multiple contributors. In a solo repo, skip the
  branch protection rules that require reviewers; CI
  status checks still apply.

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
  parallel lanes. A team-mirror recipe lands when
  we have concrete worked examples; for now,
  extending this one by adding agents to the yaml
  (and opening branch-protection on your repo)
  matches the Brunny AI 4-agent shape.

The recipe is deliberately small. If Agent OS is
doing its job, solo mode should feel like a more
structured version of your current workflow — not a
second job.
