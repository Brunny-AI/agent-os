# Postmortem Meeting

**Purpose**: Understand the root cause of an incident and prevent the CLASS of
failure, not just the specific instance.

**Duration**: 20 minutes minimum.
**Channel**: `postmortem-{incident-id}`

## Setup

```bash
python3 scripts/bus/new_channel.py --name "postmortem-{incident-id}" \
  --type "meeting" --owner "{facilitator}"
```

Each attendee creates a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

Build a timeline FIRST. No analysis until the timeline is agreed upon.

```
POSTMORTEM PRE-READ
Incident: {incident-id}
Time: {timestamp}
Attendees: {attendees}
Severity: {severity}
---
Timeline (all times in local timezone):
  {T+0}: {triggering event}
  {T+N}: {next observable event}
  {T+N}: {detection / first response}
  {T+N}: {resolution}
Impact:
  Duration: {total incident duration}
  Scope: {what was affected}
  Data: {any data loss or corruption}
Blameless framing: We are examining the system, not individuals.
```

## R1 -- Root Cause Hypothesis (50 words max)

Each agent proposes what they believe caused the incident. Use blameless
language: "the system allowed" not "{agent} failed to."

```
R1 | {agent}
Hypothesis: {50 words max, blameless language}
```

## R2 -- Challenge (75 words max)

Challenge each hypothesis. Is it the root cause or a symptom? Does it explain
the full timeline? Would fixing it prevent the class of failure?

```
R2 | {agent} -> {target-agent}
Challenge: {75 words max}
```

## 5 Whys (Facilitator-Led)

After R2, the facilitator drives a 5 Whys sequence on the strongest hypothesis.

**Stop rule**: Stop when you reach a cause that is:
- Actionable (you can change it), AND
- Structural (it is a system/process issue, not a one-time mistake)

```
Why 1: Why did {event} happen?
  -> Because {cause-1}
Why 2: Why did {cause-1} happen?
  -> Because {cause-2}
[continue until stop rule is met]
```

## Blast Radius Audit

For EVERY proposed action item, check blast radius:

```
Action: {proposed fix}
Blast radius check:
  - What else does this change affect? {list}
  - Could this fix cause a new failure? {yes/no, explain}
  - Who else needs to know? {agents/teams}
  - Is this reversible? {yes/no}
```

## Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Root cause: {confirmed root cause, blameless language}
Class of failure: {the general pattern this represents}
5 Whys chain: {abbreviated chain}
Action items (each with blast radius check):
- {agent}: {action} | Blast radius: {scope} | Reversible: {yes/no}
- {agent}: {action} | Blast radius: {scope} | Reversible: {yes/no}
Prevention:
- Rule/skill to codify: {what systemic change prevents recurrence}
- Monitoring to add: {what detection would catch this earlier}
Follow-up review: {date to verify action items completed}
NOW POSSIBLE: {what this postmortem unlocks}
```

## Closing

After synthesis:
1. Each attendee deletes their meeting cron.
2. Facilitator marks the channel as closed.
3. Action items are created as tasks with owners and deadlines.
4. If a new rule or skill is needed, it must be created before the next cycle.
