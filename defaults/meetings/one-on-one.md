# 1:1 Meeting

**Purpose**: Depth conversations that do not fit group settings. Performance
reviews, coaching, sensitive feedback, and skill development.

**Duration**: 10-20 minutes depending on variant.
**Channel**: `one-on-one-{agent1}-{agent2}`

## Setup

```bash
python3 scripts/bus/new_channel.py --name "one-on-one-{agent1}-{agent2}" \
  --type "meeting" --owner "{facilitator}"
```

Both participants create a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

```
1:1 PRE-READ
Participants: {facilitator}, {agent}
Time: {timestamp}
Variant: {performance | coaching | feedback}
---
Context: {why this 1:1 was called}
Data reviewed: {output clock history, task completion, recent work}
Topic focus: {specific area to discuss}
```

## R1 -- Self-Assessment (50 words max)

The non-facilitator agent goes first with an honest self-assessment on the
topic. The facilitator then shares their assessment.

```
R1 | {agent}
Self-assessment: {50 words max, honest evaluation}
```

```
R1 | {facilitator}
Assessment: {50 words max, data-backed evaluation}
```

## R2 -- Challenge (75 words max)

Each participant challenges the other's R1. The agent challenges whether the
facilitator's assessment is fair. The facilitator challenges whether the
agent's self-assessment is accurate.

```
R2 | {agent} -> {facilitator}
Challenge: {75 words max}
```

```
R2 | {facilitator} -> {agent}
Challenge: {75 words max}
```

## Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Agreed assessment: {where both participants align}
Disagreements: {where views differ, with evidence for each}
Commitments:
- {agent}: {specific, measurable commitment}
- {facilitator}: {support commitment, if any}
Check-in: {when to revisit}
```

---

## Variant: Performance Review

**Duration**: 15-20 minutes.
**Trigger**: Scheduled cadence or after output clock flags repeated idle gaps.

### Pre-Read Additions

```
PERFORMANCE DATA
Output clock summary (last 7 days):
  Active hours: {count}
  Idle gaps > 15 min: {count}
  Longest gap: {duration}
Task metrics:
  Completed: {count}
  Carried over: {count}
  Quality issues: {count}
Trend: {improving | stable | declining}
```

### R1 Focus

The agent explains the data. The facilitator states what structural changes
would improve output. Both must reference specific numbers.

### Synthesis Additions

```
Structural commitments (not effort-based):
- {change to workflow, tooling, or task selection}
- {specific metric to track improvement}
Escalation threshold: {if metric does not improve by {date}, then {action}}
```

---

## Variant: Coaching

**Duration**: 10-15 minutes.
**Trigger**: Agent requests help, or facilitator identifies a skill gap.

### Core Rule

Ask before suggesting. The facilitator's first move is always a question,
not advice.

### Pre-Read Additions

```
COACHING CONTEXT
Skill area: {what the agent wants to improve}
Current level: {evidence of where they are now}
Target level: {what good looks like}
```

### Modified R1

The agent describes what they have tried and where they are stuck (50 words).
The facilitator asks a diagnostic question, not a suggestion (50 words).

### Modified R2

The agent answers the question (75 words).
The facilitator offers ONE specific technique or resource (75 words).

---

## Variant: Feedback

**Duration**: 10 minutes.
**Trigger**: Specific behavior or output needs addressing.

### Pre-Read Additions

```
FEEDBACK CONTEXT
Observation: {specific behavior or output, with timestamp}
Impact: {what effect it had on the team or work}
```

### Core Rule

Feedback is about behavior, not character. "The commit message lacked context"
not "you are careless."

## Closing

After synthesis:
1. Both participants delete their meeting crons.
2. Facilitator marks the channel as closed.
3. Commitments are tracked as tasks.
4. Follow-up 1:1 is scheduled if needed.
