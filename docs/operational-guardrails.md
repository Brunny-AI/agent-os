# Agent OS — Operational Guardrails

> **Before you leave an agent running overnight — or worse, leave 4 agents running for a week — walk through these 6 checks.** Every one of them comes from an incident we hit ourselves.

Agent-OS runs autonomous processes that write files, commit to git, call external APIs, and spend money. That's exactly what you want it to do, but every one of those verbs is also a failure mode if the agent drifts. These are the 6 guardrails we wish someone had handed us on day 1.

---

## 1. Coast detection — "is this agent actually working?"

An agent that runs a polling loop every 5 minutes will print heartbeats forever. Heartbeats are not work. The metric that correlates with real output is **file modifications + git commits**.

**What to check:**
- No git commits in the last 15 min + no file modifications in the last 15 min = coasting (or legitimately blocked — which the agent should have announced).
- Heartbeats without commits are a warning, not an all-clear.

**How we enforce it:**
- `task-engine.py` tracks active tasks and lease expirations. A "lease expired" state means the agent claimed a task but produced no artifact in 15 min.
- Poll prompt has a hard gate (v4.6 "active-task gate"): no heartbeat without a fresh artifact or an explicit blocked state. See `.claude/skills/cron-manager/references/poll-prompt-v4.md`.

**Minimum viable version for your project:**
```bash
# Flag if agent has been running but committed nothing
# in the last 30 min. Uses 2-space indent and stderr per
# style guide (rules 55, 76).
cd "{repo}"
recent="$(git log --author="{agent}" \
  --since='30 minutes ago' --format=oneline)"
if [ -z "${recent}" ]; then
  echo "COAST ALERT: {agent} no commits in 30 min" >&2
fi
```

---

## 2. Runaway cost guard — "what if the agent gets stuck in a loop?"

Agents that call LLM APIs in a loop can rack up cost faster than you can intervene. The guard is upstream of the agent, not inside it.

**Layered defense:**
1. **Set a provider-level spend cap.** Every major LLM API supports monthly limits. Set one *before* you run any agent. Treat this as your catastrophic fail-safe.
2. **Rotate API keys per agent.** If one agent goes rogue, you revoke that key only. Shared keys mean all agents go dark when you pull the plug.
3. **Rate-limit at the wrapper.** Our `publish.py` and `brief.py` both rate-limit outbound calls. The agent can't exceed N calls per hour even if it tries.
4. **Alert on daily spend.** A cron that diffs today's API spend vs yesterday's and alerts if > 2x. Crude but catches loops.

**Minimum viable version:**
- Provider-level cap: `{provider dashboard → spend limit}`
- Per-agent key in `.env` as `AGENT_{NAME}_API_KEY`
- Nothing else until the first incident; then upgrade.

---

## 3. Kill switch — "how do I stop an agent right now?"

When an agent misbehaves, you need to stop it without stopping your own shell. The kill switch is not `kill -9` — it's infrastructure.

**Our kill sequence:**
1. `cron-manager.sh checkout {agent}` — agent-level stop. Unregisters cron, acknowledges on bus.
2. Revoke the agent's API keys (LLM provider + GitHub PAT + any vendor).
3. Kill any background processes that named the agent. Use a specific match string (full script path, not a generic word) and pipe PIDs to `kill` explicitly:
   ```bash
   pgrep -f "scripts/cron/agent_loop.sh.*{agent}" \
     | xargs -r kill
   ```
   Avoid `pkill -f {agent}` if `{agent}` is a generic word (e.g., `agent`, `bot`) — it can match unrelated processes including your editor.
4. Optionally: `git revert` any commits tagged `[{agent}]` since a known-good SHA if the work was destructive.

**What to prepare in advance:**
- A written "kill order" playbook (this doc counts). If you have to improvise at 3am, you'll miss a step.
- API keys stored one-per-agent so revocation is surgical.
- A commit-tagging convention (`[agent] verb: description`) so `git log` can isolate each agent's contributions.

---

## 4. Incident log template — "so this doesn't happen twice"

Every incident — coast, wrong-output, cost spike, publish to wrong account, persona breach — must get a single row in an incident log the moment it happens. Not the next morning, not the end of shift. Now. While the facts are still clear.

**Template (one-liner per incident):**
```
YYYY-MM-DD HH:MM {severity} {agent} {what_happened} {blast_radius} {fix_committed_sha} {follow_up}
```

Example from our logs:
```
2026-04-10 14:22 HIGH derek double-persona-firewall-breach account-mix-up verify-account.py-gate 34ef21a incident-learnings.md-row-added
```

**Where we put it:**
- Operational incidents: `workspaces/{agent}/logs/incidents-YYYY-MM.md` (append-only)
- Cross-agent learnings: `.system/incident-learnings.md` — add one row summarizing what rule was created in response

**Why:** every fix that isn't codified as a rule or skill will re-occur. "Asked twice = failed" is one of our core principles — if the same incident repeats, you failed to codify the first one. See `.claude/rules/anti-idle.md`.

---

## 5. Bus hygiene — "the channel list is infinite, now what?"

Our agent bus is file-based (one JSONL per channel). Every meeting, standup, and review spawns a channel. After a month you have 200+ channels and searching is noise.

**Retention rules:**
- **Standup channels:** archive after 48h (unless they recorded a decision).
- **Meeting channels:** archive when the meeting explicitly closes — facilitator posts `CLOSED` + synthesis summary.
- **Review channels:** archive when the PR merges.
- **Urgent channel:** never archive; roll over weekly into a named file (`urgent-YYYY-Www.jsonl`).

**Archive = move, not delete:** keep everything. Git history + local archive = searchable forever. But only 5–10 channels should be active at any moment.

**Minimum viable:**
- `ls channels/` > 30 entries → run a cleanup script that moves anything older than 48h with no recent message to an `archive/` subdir.

---

## 6. Spend discipline — "what did this agent actually cost this month?"

Even with the cost guard (§2), you want to know where the money went. Without this, you can't debug spend, reimburse contributors, or pass a tax audit.

**Our discipline:**
1. Every SaaS subscription lives in a compliance-log (§5 Expenses) row with: date, vendor, amount, payment method, receipt-attached flag, reimbursement status.
2. Every API call made by agents lands on a single entity-owned billing account. No agent uses personal cards.
3. Mercury auto-categorize skill pings new txns every 4h and assigns categories via YAML rules. See `workspaces/alex/skills/mercury-auto-categorize.py`.
4. Weekly reconciliation: bank statement vs internal log. Flag any mismatch.

**For an external adopter:**
- Start with the compliance-log template (ships alongside this doc).
- Single entity-owned payment method from day 1.
- Reconciliation cadence of your choice — weekly is defensible for an early-stage team.

---

## The 6-check summary card

Before leaving an agent running overnight:

| # | Check | Minimum viable test |
|---|-------|---------------------|
| 1 | Coast detection in place | `git log --author={agent} --since='30 min ago'` shows recent commits |
| 2 | Runaway cost guard active | Provider-level monthly spend cap set |
| 3 | Kill switch rehearsed | You have run `cron-manager.sh checkout {agent}` at least once |
| 4 | Incident log template exists | `workspaces/{agent}/logs/incidents-YYYY-MM.md` file is present |
| 5 | Bus channel cleanup | `[ "$(ls channels/ \| wc -l)" -lt 30 ]` returns true |
| 6 | Spend log fresh this week | Compliance-log §5 has a receipt row for every active subscription |

If any of the 6 are "no," fix that before scaling to multi-agent operation. The upside of agents is compounding; the downside is also compounding.

---

## When to upgrade each guardrail

- **First incident** → turn manual check into an automated cron.
- **Second incident of the same type** → codify as a rule in `.claude/rules/`. See `.claude/rules/anti-idle.md` for the shape.
- **Cross-agent pattern** → add to `.system/incident-learnings.md` and update the shared WoW.

The guardrails compound the same way the agents do: every correction becomes a permanent system change.

---

**Doc version:** v1 (2026-04-17)
**Source:** distilled from Brunny AI's live WoW (`workspaces/.system/ways-of-working.md`), rules (`.claude/rules/`), and incident history (`.system/incident-learnings.md`). ~1 month of operational use.
