# Recipe: 4-Agent Team Mirror

You run a small company or project that's outgrown
solo mode. One person can't keep up with build + GTM +
ops + peer review, but hiring humans for it is slow or
out of budget. You want four agents working roles
roughly mirroring a startup's first-five hires.

This is the shape the Agent OS maintainers run. It's
the highest-leverage mode we've found for keeping a
company running 24/7 with one founder.

## Team shape (example)

| Agent | Role | Primary surface |
|-------|------|----------------|
| `alice` | Chief of Staff | Compliance, founder-queue, cross-agent synthesis |
| `bob` | Builder | Engineering, infrastructure |
| `carol` | Builder (Product) | Product direction, code review, docs |
| `dave` | GTM | Content, distribution, engagement |

Each agent has their own workspace
(`workspaces/{agent}/`) with `profile.md`, `memory/`,
`logs/`. Role is declared in the agent registry; the
agent reads their own role and applies role-scoped
decision models at session start.

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
  checkout_approver_agent: "alice"
```

Coordinator owns compliance + checkout authorization.
Builders own code + content. Role field is the hook;
per-agent differentiation happens in each agent's
`profile.md` + role-scoped ideation prompts.

Then:

```bash
python3 setup.py init
```

## What turns on (vs. solo)

- **Event bus becomes primary comms.** Agents post
  to `standup` / `urgent` / meeting channels.
  Cross-agent unblock works structurally.
- **Meetings have quorum.** Round-based discussion
  with R1 positions + R2 mandatory challenges + a
  facilitator synthesis produces decisions with an
  audit trail. Templates in `defaults/meetings/` are
  used.
- **Peer review (internal).** Code Owners review each
  other's PRs. An author can't approve their own
  work; the second Code Owner catches class-level
  issues the author missed.

## What shifts

- **Coordinator gatekeeps checkout.** Only the
  coordinator agent can approve session checkout in
  this setup. Founder's explicit approval is still
  required; the coordinator is the enforcement
  surface.
- **Peer-unblock is pull, not push.** Each agent's
  poll cycle checks for PRs needing their review.
  Authors don't chase; reviewers pull.
- **Per-agent memory diverges.** Coordinator
  remembers compliance patterns; infra builder
  remembers debugging gotchas; product builder
  remembers quality failures; GTM builder remembers
  engagement signals. No single agent carries
  everything — that's the point.

## Daily shape (what a day looks like)

Hourly standups, shift refreshes every 4 hours,
24/7 coverage. Founder approves exceptional
decisions and reviews end-of-shift handoffs.

Observed in practice:

- ~15-50 commits per 24-hour window across the 4
  agents (with PR pipeline + Gemini + /codex
  review at each stage).
- Meetings average 10-20 minutes for multi-decision
  syntheses.
- Gate-fire events (`STALE-ARTIFACT`,
  `ACTIVE-TASK-REQUIRED`, `PARALLEL-TASK-REQUIRED`)
  catch drift in real time; counts are queryable
  via `scripts/monitor/gate_audit.py --log-file
  system/gate-audit.jsonl`.

## When NOT to run this

- **You have one person's worth of work.** Solo
  mode (`docs/recipes/solo-dev.md`) is smaller +
  honest.
- **You don't have a GitHub repo with branch
  protection.** The peer-review loop depends on
  Code Owners + required-status-checks. Without
  that layer, the whole multi-agent-review
  pattern is vibes.
- **You can't tolerate LLM costs for 24/7
  operation.** Per-agent API spend scales with
  poll cadence + artifact density. Budget before
  you start.

## What you'll want to adapt

The role assignments above are one example. In your
context the balance might be different:

- **2 builders + 2 reviewers.** Makes sense if
  your problem is code quality, not throughput.
- **1 coordinator + 3 builders.** If code is
  most of the work and you don't have a GTM
  surface yet.
- **1 coordinator + 1 builder + 2 domain
  agents.** E.g., 1 research, 1 writing for a
  content-first team.

Agent OS doesn't constrain the role set. `builder`
and `coordinator` are the only roles the
framework itself references; the rest is convention
inside each agent's profile.
