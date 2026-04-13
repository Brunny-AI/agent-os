# Design Constraints

## Dependency Rules
- ZERO external dependencies beyond Python stdlib,
  Bash, and Claude Code
- No pip install. No npm. No Docker.
- No databases (SQLite included). Files only.
- No message queues. JSONL append-only logs.
- No cloud services. Everything runs local.
- If a feature requires a new dependency, it does
  not ship. Find a file-based alternative.

## File Format Rules
- Config: YAML (agent-os.yaml, registry.yaml)
- Messages: JSONL (one JSON object per line)
- State: JSON (cron-registry, task-engine-state,
  bus-offsets)
- Logs: Markdown (activity, audit) or JSONL (events)
- Templates: Markdown (poll prompts, meeting guides)
- Every structured file: schema_version field

## Code Standards
- Python: 4-space indent, 80 char lines, Google
  naming, type annotations on public APIs,
  f-strings, grouped imports (stdlib/third-party/
  local), no bare except, no mutable defaults
- Bash: 2-space indent, 80 char lines, quote all
  vars, local for variables, readonly for constants,
  errors to stderr, scripts >100 lines should be
  Python

## Concurrency Model
- File locking via fcntl (LOCK_EX) for shared state
- Max-merge for bus offsets (never regress)
- Atomic writes: tmp file + mv (never partial reads)
- No threads. No async. One process per agent.
- Shift refresh: hard kill + restart, not graceful
  handover. No two agents own the same task.

## Bus Design
- Append-only. Never mutate or delete messages.
- At-least-once delivery via peek/commit
- TTL-based expiration (lazy filtering at read)
- Weekly partitions for log rotation
- Offset per-agent, per-channel, per-week

## Task Engine Design
- 15-min lease, renewed on each artifact
- Finish-to-start: complete(N) requires claim(N+1)
- Adjacent-possible scan after every completion
- Blocked tasks: record blocker, claim fallback
- No idempotency keys in MVP (v2 when external
  side effects are introduced)

## Output Clock Design
- Filesystem timestamps are ground truth
- Exclude infrastructure files (offsets, registry,
  locks, CLAUDE.md)
- BUILDING > WORKING > STALE > IDLE
- 3 consecutive identical snapshots = STALE
- Peer monitoring: every agent checks every agent
