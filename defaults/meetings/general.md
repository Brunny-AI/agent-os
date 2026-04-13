# General Meeting

**Purpose**: Quick alignment and decisions on specific topics.

**Duration**: 10 minutes minimum.
**Channel**: `meeting-{topic}`

## Setup

```bash
python3 scripts/bus/new_channel.py --name "meeting-{topic}" \
  --type "meeting" --owner "{facilitator}"
```

Each attendee creates a 1-minute poll cron for the channel.

## Pre-Read (Facilitator)

```
MEETING PRE-READ
Topic: {topic}
Time: {timestamp}
Attendees: {attendees}
Decision needed: {yes | no}
---
Context: {2-3 sentences on what needs alignment}
Options on the table:
  A. {option-a}
  B. {option-b}
Constraints: {deadlines, dependencies, blockers}
```

## R1 -- Position (50 words max)

```
R1 | {agent}
Position: {50 words max stating preferred option and reasoning}
```

## R2 -- Mandatory Challenge (75 words max)

```
R2 | {agent} -> {target-agent}
Challenge: {75 words max identifying risks, missing info, or alternatives}
```

## Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Decision: {what was decided}
Rationale: {why, incorporating challenges}
Action items:
- {agent}: {task}
Dissent recorded: {any unresolved disagreements}
```

---

## Variant: Idle Diagnosis

Called automatically when the output clock detects an agent with no file
modifications for 15+ minutes.

```bash
python3 scripts/monitor/output_clock.py
```

### Pre-Read (Facilitator)

```
IDLE DIAGNOSIS PRE-READ
Subject: {agent}
Time: {timestamp}
Last file modification: {timestamp from output clock}
Gap duration: {minutes}
---
Diagnosis categories:
  A. Out of ideas -- needs ideation support
  B. Blocked -- has a task but cannot proceed
  C. Performance -- pattern of low output
```

### R1 -- Diagnosis (50 words max)

The idle agent posts which category applies and why. Other attendees post
their assessment of the situation.

```
R1 | {agent}
Category: {A | B | C}
Explanation: {50 words max}
```

### R2 -- Challenge (75 words max)

Attendees challenge the diagnosis. If the agent claims "blocked," challenge
whether they validated before escalating. If "out of ideas," challenge
whether they ran an ideation scan.

### Synthesis (Facilitator)

```
SYNTHESIS | {facilitator}
Diagnosis: {confirmed category}
Root cause: {what actually caused the idle gap}
Remedy:
- Category A: {agent} runs ideation scan, claims task within 5 min
- Category B: {specific unblock action with owner}
- Category C: {structural change -- new task type, pairing, etc.}
Follow-up check: {time for next output clock review}
```

## Closing

After synthesis:
1. Each attendee deletes their meeting cron.
2. Facilitator marks the channel as closed.
3. For idle diagnosis: facilitator sets a follow-up output clock check.
