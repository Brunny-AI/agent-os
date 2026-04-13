# Architecture

How Agent OS components work together.

## Data Flow

```
Claude Code session
  |
  +--> CronCreate (poll every 5 min)
  |      |
  |      +--> Bus read (peek/commit)
  |      +--> Output clock (idle check)
  |      +--> Task engine (lease check)
  |      +--> Cron manager (heartbeat)
  |
  +--> CronCreate (scheduler every 60 min)
  |      |
  |      +--> agent-schedule.json tasks
  |      +--> Shift boundary detection
  |
  +--> Agent does work
         |
         +--> Bus send (messages)
         +--> Task engine (claim/artifact/complete)
         +--> Git commit (proof of work)
```

## Component Interactions

### Event Bus

The bus is append-only JSONL files organized by
channel and ISO week.

```
system/bus/
  channels/
    standup/
      manifest.json    # Channel metadata
      2026-W15.jsonl   # This week's messages
      2026-W14.jsonl   # Last week's archive
    urgent/
      ...
  receipts/
    alice.json         # Read receipts per agent
```

**Delivery model:** At-least-once via peek/commit.
Agents peek at new messages, process them, then
commit their offset. If an agent crashes between
peek and commit, it re-reads the same messages.

**Concurrency:** All writes use `fcntl.flock(LOCK_EX)`
for mutual exclusion. Reads are lock-free (JSONL is
append-only, so reads see consistent data). The last
line may be a partial write from a concurrent sender;
readers handle this by catching `JSONDecodeError` on
the final line and retrying on the next read.

**Rotation:** Weekly partitions by ISO week key.
The `snapshot.py` script closes the current week
and opens the next one.

### Cron Manager

Tracks agent liveness through heartbeats. Each agent
registers its poll and scheduler cron jobs, then sends
heartbeats on every tick.

```
system/cron-registry.json
{
  "schema_version": 2,
  "jobs": [
    {
      "agent": "alice",
      "type": "poll",
      "job_id": "abc123",
      "last_heartbeat": "2026-04-13T09:07:00Z",
      "timeout_minutes": 15
    }
  ]
}
```

**Detection:** If `now - last_heartbeat > timeout`,
the agent is EXPIRED. Teammates detect this during
their polls and alert on the urgent channel.

**Shift refresh:** When session age exceeds
`shifts.duration_hours` (default 4h), the scheduler
triggers a shift refresh: retro, handoff, commit,
then the sidecar restarts the process with fresh
context.

### Task Engine

Enforces continuous work through finish-to-start
constraints.

**States:**

```
READY --> CLAIMED --> IN_PROGRESS --> COMPLETE
             |            |
             +-----+------+
                   |
             BLOCKED / EXPIRED
```

**Invariant:** `complete(task_n)` requires that
another task is CLAIMED or IN_PROGRESS with at least
one artifact. You cannot finish a task without having
already started the next one. (The "final task" case
is handled by claiming a follow-up from the
adjacent-possible scan before completing.)

**Leases:** Each claim starts a 15-minute timer.
Producing an artifact renews the lease. If the lease
expires without an artifact, the task becomes EXPIRED.

**Initiative counter:** Every 3 completed tasks,
the engine prompts for a self-directed leverage
proposal (not just assigned work).

### Output Clock

Detects idle agents by filesystem timestamps and
git history.

**Status levels (highest to lowest):**
1. BUILDING: git commits in the look-back window
2. WORKING: file modifications but no commits
3. STALE: same modified files for 3+ consecutive
   polls (gaming detection)
4. IDLE: no commits and no file modifications

**Exclusions:** Infrastructure files (bus offsets,
cron registry, lock files, CLAUDE.md) don't count
as output. Only real deliverables matter.

**Stale detection:** The output clock saves a
snapshot of modified files after each check. If the
snapshot is identical 3 times in a row, the agent
is marked STALE (same files touched repeatedly
without progress).

### Config Loader

Recursive merge of defaults and user overrides.

```
defaults/agent-os.yaml  (shipped, read-only)
       +
config/agent-os.yaml   (user, gitignored)
       =
     merged config     (what scripts read)
```

**Merge rules:**
- Nested dicts merge recursively (key-by-key)
- Lists replace (not append)
- Scalars overwrite
- User config only needs changed keys

**YAML parser:** Uses PyYAML if installed, otherwise
falls back to a custom stdlib-only parser. No
external dependencies are required (PyYAML is
optional for better edge-case handling).

## File Formats

| Format | Used for | Schema |
|--------|----------|--------|
| JSONL | Bus messages, channel index | One JSON object per line |
| JSON | State files, manifests, receipts | `schema_version` field required |
| YAML | Config, registry | Parsed by custom loader |
| Markdown | Profiles, logs, docs, templates | Human-readable |

All structured files include a `schema_version` field
for future migration tooling.

## Concurrency Model

- One Claude Code process per agent (no threading)
- File locking via `fcntl.flock(LOCK_EX)` for shared
  state (bus offsets, cron registry, task engine)
- Atomic writes for state files: write to temp file,
  `os.replace()` to target. Bus uses append-only
  writes under flock (not atomic replacement).
- Bus offsets use max-merge: concurrent writers can
  never regress another agent's read position

## Autonomous Mode

Interactive mode (default) requires manual session
management. Autonomous mode adds a wrapper that runs
Claude in a loop, refreshing context automatically.

```
agent_loop.sh (wrapper, runs forever)
  |
  +--> Shift 1: Claude + /session-start
  |      |
  |      +--> Sidecar watches for flag file
  |      +--> Agent hits 4h boundary
  |      +--> Agent: retro + handoff + shift_refresh.sh
  |      +--> Sidecar: detects flag, kills Claude
  |
  +--> Shift 2: Claude + /session-refresh
  |      |
  |      +--> Reads handoff, restores crons
  |      +--> Resumes work with fresh context
  |      +--> (repeat)
  |
  +--> Crash detection
         |
         +--> Rapid exit? Exponential backoff
         +--> 3 rapid exits? CRASH LOOP, stop + alert
```

**Sidecar pattern:** Claude Code refuses to kill its
own parent process (safety guardrail). The sidecar
runs as a background subshell, watches for a flag
file, and sends SIGTERM externally.

**Race mitigations:**
1. Atomic flag write (tmp + mv)
2. Git lock check before kill
3. Grace period for I/O completion
4. Process name verification
5. SIGTERM with SIGKILL escalation (10s timeout)

**External monitoring:** `watchdog.sh` runs outside
Claude (via launchd or system cron). Checks heartbeats
and auto-restarts dead agents in screen/tmux sessions.

## Runtime vs Source Boundary

```
SOURCE (committed to git):
  defaults/    scripts/    docs/    examples/
  setup.py     CLAUDE.md   README.md

RUNTIME (gitignored, created by setup.py):
  system/      workspaces/  config/
```

Source tree contains only immutable product code.
Runtime directories contain per-deployment state.
This separation means `git pull` never overwrites
user data.
