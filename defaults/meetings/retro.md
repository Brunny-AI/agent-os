# Retrospective Meeting

**Purpose**: Identify patterns over a longer time horizon. Not about individual
incidents (use postmortem for that) but about recurring themes in how the team
works.

**Duration**: 20 minutes minimum.
**Channel**: `retro-YYYY-MM-DD`
**Cadence**: Weekly or end-of-sprint.

## Setup

```bash
python3 scripts/bus/new_channel.py --name "retro-$(date +%Y-%m-%d)" \
  --type "meeting" --owner "{facilitator}"
```

Each attendee creates a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

Gather evidence before the meeting. Opinions without data are noise.

```
RETRO PRE-READ
Period: {start-date} to {end-date}
Time: {timestamp}
Attendees: {attendees}
---
Evidence summary:
  Tasks completed: {count}
  Tasks carried over: {count}
  Incidents: {count}
  Idle gaps detected: {count, from output clock}
  Skills/rules created: {list}
  Skills/rules modified: {list}
Patterns observed by facilitator:
  1. {pattern-1 with supporting data}
  2. {pattern-2 with supporting data}
```

## R1 -- Reflection (50 words max)

Each agent answers ONE of the following, backed by evidence:

- **Worked well**: a practice or decision that produced measurable results.
- **Did not work**: something that failed or underperformed, with data.
- **Honest gap**: something the agent should have done but did not.

```
R1 | {agent}
Category: {worked-well | did-not-work | honest-gap}
Evidence: {50 words max, with specific examples or metrics}
```

## R2 -- Pattern Challenge (75 words max)

Challenge whether the observation is a one-off or a pattern. Ask: has this
happened before? Is there a structural cause? Would the proposed change
actually fix it?

```
R2 | {agent} -> {target-agent}
Challenge: {75 words max}
```

## Pre-Mortem

Before closing, the facilitator runs a pre-mortem on the coming week/sprint:

```
PRE-MORTEM
Assume the next cycle fails. What is the most likely cause?
Each agent posts one risk (25 words max):
  {agent}: {risk}
Mitigation assigned:
  {agent}: {mitigation action for highest-voted risk}
```

## Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Patterns confirmed:
- {pattern}: {evidence across multiple data points}
Patterns rejected:
- {observation}: one-off, not structural
Commitments for next cycle:
- {agent}: {specific, measurable commitment}
- {agent}: {specific, measurable commitment}
System changes:
- New rule: {rule to add to prevent recurring issue}
- Skill update: {skill to modify}
- Process change: {workflow adjustment}
Top risk for next cycle: {from pre-mortem}
Mitigation owner: {agent}
NOW POSSIBLE: {what these insights unlock}
```

## Closing

After synthesis:
1. Each attendee deletes their meeting cron.
2. Facilitator marks the channel as closed.
3. System changes (rules, skills) are implemented before the next cycle begins.
4. Commitments are tracked as tasks with deadlines.
