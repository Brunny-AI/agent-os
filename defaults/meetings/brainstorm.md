# Brainstorm Meeting

**Purpose**: Divergent thinking. Generate many options before converging on the
best ones. Quality comes from quantity first.

**Duration**: 20 minutes minimum.
**Channel**: `brainstorm-{topic}`

## Setup

```bash
python3 scripts/bus/new_channel.py --name "brainstorm-{topic}" \
  --type "meeting" --owner "{facilitator}"
```

Each attendee creates a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

```
BRAINSTORM PRE-READ
Topic: {topic}
Time: {timestamp}
Attendees: {attendees}
---
Problem statement: {clear, specific problem to solve}
Constraints:
- {constraint-1}
- {constraint-2}
What good looks like: {success criteria}
Adjacent work: {related tasks or systems that may inspire ideas}
Rule: No idea is too wild in R1. Convergence happens in R2.
```

## R1 -- Diverge: Positions (50 words max)

Each agent proposes a distinct approach. Aim for variety -- if your idea
overlaps with someone else's, pivot to something different.

```
R1 | {agent}
Idea: {50 words max, one concrete proposal}
```

## R2 -- Converge: Challenge, Extend, or Combine (75 words max)

Each agent responds to ONE other agent's R1 with exactly one of:

- **Challenge**: identify a flaw, risk, or missing assumption.
- **Yes AND**: accept the idea and extend it with a specific addition.
- **Combine**: merge two R1 ideas into something stronger.

"I agree" is not valid. "This is great" is not valid. Add substance.

```
R2 | {agent} -> {target-agent}
Mode: {challenge | yes-and | combine}
Response: {75 words max}
```

## Pre-Mortem

Before finalizing, stress-test the top ideas:

```
PRE-MORTEM
For each top idea, assume it ships and fails. Why did it fail?
  Idea: {idea-summary}
  Failure mode: {what went wrong}
  Likelihood: {high | medium | low}
  Prevention: {what would prevent this failure}
```

The pre-mortem is not optional. Ideas that survive pre-mortem are stronger.
Ideas that do not survive are killed early, which is the point.

## Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Ideas generated: {count}
Top ideas after convergence:
  1. {idea} -- survived pre-mortem, {agent} owns next step
  2. {idea} -- survived pre-mortem, {agent} owns next step
Ideas killed by pre-mortem:
  - {idea}: {failure mode that killed it}
Ideas parked for later:
  - {idea}: {why it is not actionable now}
Action items:
  - {agent}: {concrete next step for top idea}
NOW POSSIBLE: {what these ideas unlock}
```

---

## Variant: Idle Diagnosis Brainstorm (Category A)

When the output clock flags an agent as idle and the diagnosis is Category A
(out of ideas), run this variant instead of a standard brainstorm.

```bash
python3 scripts/monitor/output_clock.py
```

### Pre-Read (Facilitator)

```
IDLE BRAINSTORM PRE-READ
Subject: {idle-agent}
Time: {timestamp}
Last file modification: {timestamp from output clock}
---
Diagnosis: Category A -- out of ideas
{idle-agent}'s recent work: {summary of last 3-5 tasks}
Team backlog: {current open tasks}
Adjacent possibilities: {systems or skills near completion that could inspire}
Goal: Generate 5+ concrete task ideas for {idle-agent}.
```

### Modified R1 and R2

R1: Each agent (including the idle agent) proposes a task the idle agent
could start immediately. Tasks must be concrete and completable.

R2: Challenge feasibility. Can the idle agent actually do this? Does it
produce value? Is there a dependency that blocks it?

### Synthesis

The idle agent claims one task from the synthesis before the meeting closes.
No meeting ends with the idle agent still without work.

## Closing

After synthesis:
1. Each attendee deletes their meeting cron.
2. Facilitator marks the channel as closed.
3. For idle brainstorms: the idle agent must claim a task within 5 minutes.
