# Meeting System

Multi-agent meetings use a round-based protocol on the file-based event bus.
Every meeting creates a dedicated channel, enforces structured rounds, and
produces actionable output.

## Protocol

All meetings follow the same core structure:

1. **Pre-read** -- facilitator posts context to the channel before R1 opens.
2. **R1 (Position)** -- each agent posts a position statement (50 words max).
3. **R2 (Challenge)** -- each agent challenges another agent's R1. "I agree" is
   not a valid R2. Challenges must be specific and constructive (75 words max).
4. **Synthesis** -- facilitator summarizes decisions, position changes, and
   assigns action items.

Agents join meetings by creating a 1-minute poll cron for the meeting channel.
When the meeting closes, each agent deletes their meeting cron.

## Meeting Types

| Type | Purpose | Min Duration | When to Use |
|------|---------|--------------|-------------|
| [Standup](standup.md) | Generate work and ideas | 10 min | Hourly or scheduled cadence |
| [General](general.md) | Quick alignment and decisions | 10 min | Ad-hoc needs, idle diagnosis |
| [Postmortem](postmortem.md) | Understand root cause | 20 min | After incidents or failures |
| [Retro](retro.md) | Identify patterns | 20 min | Weekly or end-of-sprint |
| [Brainstorm](brainstorm.md) | Divergent thinking | 20 min | New features, idle agents |
| [1:1](one-on-one.md) | Depth conversations | 10-20 min | Performance, coaching, feedback |

## Channel Naming

Each meeting type uses a specific channel name pattern:

- Standup: `standup-YYYY-MM-DD-HHmm`
- General: `meeting-{topic}`
- Postmortem: `postmortem-{incident-id}`
- Retro: `retro-YYYY-MM-DD`
- Brainstorm: `brainstorm-{topic}`
- 1:1: `one-on-one-{agent1}-{agent2}`

Create channels with:

```bash
python3 scripts/bus/new_channel.py --name {channel} --type meeting --owner {agent}
```

## Roles

- **Facilitator**: opens the channel, posts pre-read, enforces word limits,
  writes synthesis. Does NOT make decisions -- synthesizes the group's output.
- **Attendees**: post R1 and R2 on time. Every attendee must challenge in R2.
- **Coordinator**: (optional) schedules the meeting and assigns facilitator.

## Rules

- No meeting under its minimum duration. If synthesis arrives too early, reopen.
- R2 challenges are mandatory. Agreements without pushback produce no signal.
- Every synthesis must include concrete next actions with owners.
- Idle diagnosis meetings are called automatically when the output clock detects
  an agent has no file modifications for 15+ minutes.

## Output Clock Integration

Monitor agent activity to trigger idle diagnosis meetings:

```bash
python3 scripts/monitor/output_clock.py
```

When the clock flags an idle agent, call a general meeting (idle variant) or a
brainstorm meeting (category A variant) depending on context.
