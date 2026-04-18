# Recipe: 4-Agent Team Mirror

You run a small company or project that's outgrown solo
mode. One person can't keep up with build + GTM + ops +
peer review, but hiring humans for it is slow or out of
budget. You want four agents working roles roughly
mirroring a startup's first-five hires.

This is the shape the Agent OS maintainers run. It's
the highest-leverage mode we've found for keeping a
company running 24/7 with one founder.

## Team shape (example)

| Agent | Role | Primary surface |
|-------|------|----------------|
| `alice` | Coordinator (CoS) | Compliance, founder-queue, cross-agent synthesis |
| `bob` | Builder | Engineering, infrastructure |
| `carol` | Builder (Product) | Product direction, code review, docs |
| `dave` | Builder (GTM) | Content, distribution, engagement |

Each agent has its own workspace at
`workspaces/{agent}/` with `profile.md`, `memory/`,
`logs/`. Per-agent differentiation (decision models,
domain focus, tone) lives in each agent's own
`CLAUDE.md` and `profile.md` — you edit those after
`setup.py init` runs.

> **Shipping note (v0.2):** Agent OS currently ships
> two roles: `builder` and `coordinator`. Other
> role-level specialization (reviewer permissions,
> role-scoped ideation prompts) lands in later
> releases. For now, model specialization via the
> per-agent `CLAUDE.md` and the example `profile.md`
> stubs `setup.py init` writes.

## Configuration

Create `config/agent-os.yaml`:

```yaml
team:
  name: "company"
  agents:
    - name: "alice"
      role: "coordinator"
    - name: "bob"
      role: "builder"
    - name: "carol"
      role: "builder"
    - name: "dave"
      role: "builder"

governance:
  # The coordinator owns checkout authorization. When
  # a session sends a checkout signal, the checkout
  # flow looks for a recent approval message from
  # this agent on the bus.
  checkout_approver_agent: "alice"
```

Then:

```bash
python3 setup.py init
```

That writes one workspace per agent (with `CLAUDE.md`
and `profile.md` stubs keyed on role), default bus
channels (`standup`, `urgent`), an empty cron
registry, and the merged `.claude/rules/` set.

## Post-init: per-agent authoring

Open each workspace's `profile.md` and write the
agent's identity:

- Name, role, domain they own
- Decision models (how they break ties)
- Known drift pattern (when they go passive)
- Anchor question (the re-read on every session start)

Then edit `CLAUDE.md` to point at the files they
read at session start (`profile.md`, role-relevant
sections of `defaults/rules/`, any per-agent
`memory/` files). Without this authoring, the agents
boot as generic builders or coordinators; with it,
they have durable identity across shifts.

## What turns on (vs. solo)

- **Event bus becomes primary comms.** Agents post
  to `standup` / `urgent` / meeting channels.
  Cross-agent unblock works structurally.
- **Meetings have quorum.** Round-based discussion
  with R1 positions + R2 mandatory challenges + a
  facilitator synthesis produces decisions with an
  audit trail. Templates in `defaults/meetings/`
  supply the format.
- **Peer review on shared repos.** Configure GitHub
  branch protection with CODEOWNERS + required
  status checks. Agents cross-approve each other's
  PRs via the standard GitHub flow; `pr-workflow`
  rule (in `defaults/rules/`) captures the expected
  review discipline.

## What's a convention, not a framework feature

These are operational patterns the Agent OS team
follows but that the current framework doesn't
enforce structurally:

- **Coordinator as checkout approver.** The
  `governance.checkout_approver_agent` setting
  chooses who approves. The framework verifies a
  recent bus message from that approver before
  completing checkout; founder-level authorization
  beyond that is an operational convention, not a
  framework gate.
- **Peer PRs pulled on each poll cycle.** Agent OS
  polls don't yet ship a "scan PRs awaiting your
  review" step in the default poll prompt — that
  pattern is maintained per-team in
  `workspaces/{agent}/` poll prompt overrides. A
  generic version is on the v0.3 roadmap.
- **Per-role poll prompts.** Coordinators and
  builders benefit from different gate ordering
  (compliance-first vs. task-first). Ships per-team
  today; role-keyed defaults are a v0.3 candidate.

## Daily shape

Hourly standups, shift refreshes every 4 hours, 24/7
coverage. Founder approves exceptional decisions and
reviews end-of-shift handoffs.

Observed in practice (Agent OS team, April 2026):

- ~15-50 commits per 24-hour window across the 4
  agents (with PR pipeline + Gemini + /codex
  review at each stage).
- Meetings average 10-20 minutes for
  multi-decision syntheses.
- Gate-fire events (`STALE-ARTIFACT`,
  `ACTIVE-TASK-REQUIRED`, `PARALLEL-TASK-REQUIRED`)
  catch drift in real time. Instrumentation +
  daily aggregator tooling is in flight and lands
  as part of v0.2.

## When NOT to run this

- **You have one person's worth of work.** Solo
  mode is smaller and honest — see
  `docs/recipes/solo-dev.md` (shipping alongside
  this recipe in v0.2).
- **You don't have a GitHub repo with branch
  protection.** The peer-review loop depends on
  Code Owners + required status checks. Without
  that layer, the whole multi-agent-review pattern
  is vibes.
- **You can't tolerate LLM costs for 24/7
  operation.** Per-agent API spend scales with
  poll cadence + artifact density. Budget before
  you start.

## What you'll want to adapt

The role assignments above are one example. Common
variations:

- **2 builders + 2 coordinators.** Makes sense if
  your problem is code quality and there are two
  review-heavy domains (e.g., security + product).
- **1 coordinator + 3 builders.** If code is most
  of the work and you don't have a GTM surface
  yet.
- **1 coordinator + 1 builder + 2 domain
  agents.** E.g., 1 research, 1 writing for a
  content-first team. The `role: "builder"` field
  is neutral about domain — domain lives in
  `profile.md`.

Agent OS doesn't constrain role semantics. `builder`
and `coordinator` are the role keys the framework
references in `defaults/` today; domain-level
specialization (reviewer, GTM, research) lives per-
agent in `profile.md`.

## Next steps

- Walkthrough a first session: `docs/recipes/solo-dev.md` (shipping v0.2)
- Dependencies: `docs/install.md`
- Rules your agents will follow: `defaults/rules/`
- Workflow customization: `examples/workflows/`
