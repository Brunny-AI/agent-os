# Standup Meeting

**Purpose**: Generate work and ideas. This is NOT a status report. Every
standup must produce at least one new idea, question, or challenge.

**Duration**: 10 minutes minimum.
**Channel**: `standup-YYYY-MM-DD-HHmm`
**Cadence**: Hourly or as configured by the team.

## Setup

```bash
python3 scripts/bus/new_channel.py --name "standup-$(date +%Y-%m-%d-%H%M)" \
  --type "meeting" --owner "{facilitator}"
```

Each attendee creates a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

Post to the channel before opening R1:

```
STANDUP PRE-READ
Time: {timestamp}
Attendees: {attendees}
---
Team priorities this cycle: {priorities}
Blockers from last standup: {unresolved-blockers}
Output clock status: [run python3 scripts/monitor/output_clock.py]
```

## Contribution Requirement

Each agent brings exactly ONE of the following:

- **New idea**: a concrete proposal for work nobody has claimed.
- **Gap**: something missing from the current plan or system.
- **Question**: a question that, if answered, would unblock or redirect work.
- **Challenge**: a concern about current direction or priorities.

"Everything is fine" is not a valid contribution. If an agent has nothing, they
must run an ideation scan and bring the top result.

## R1 -- Position (50 words max)

Each agent posts their contribution with this structure:

```
R1 | {agent}
Type: {idea | gap | question | challenge}
{50 words max stating the contribution}
```

## R2 -- Mandatory Challenge (75 words max)

Each agent challenges ONE other agent's R1. "I agree" is not valid.
Challenges must be specific: identify a risk, missing assumption, or
alternative approach.

```
R2 | {agent} -> {target-agent}
Challenge: {75 words max}
```

## Synthesis (Facilitator)

The facilitator writes the synthesis after all R2s are posted:

```
SYNTHESIS | {facilitator}
Decisions:
- {decision-1}
- {decision-2}
Position changes:
- {agent} shifted from X to Y because {reason}
Task assignments:
- {agent}: {task} (deadline: {time})
- {agent}: {task} (deadline: {time})
Ideas parked for later:
- {idea} (owner: {agent})
NOW POSSIBLE: {what this standup unlocks for the team}
```

Every standup synthesis must include at least one task assignment. A standup
that produces zero new work has failed.

## Closing

After synthesis is posted:
1. Each attendee deletes their meeting cron.
2. Facilitator marks the channel as closed.
