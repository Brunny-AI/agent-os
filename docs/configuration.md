# Configuration Guide

Agent OS uses override-based configuration. You
never edit the defaults -- you create a `config/`
file with only the values you want to change.

## How It Works

```
defaults/agent-os.yaml   <-- shipped, read-only
config/agent-os.yaml     <-- your overrides
```

Scripts read the merged result. Your overrides take
priority. Missing keys fall back to defaults.

## Creating Your Config

After running `python3 setup.py init`, create
`config/agent-os.yaml`:

```yaml
schema_version: 1

team:
  name: "acme-ai"
  agents:
    - name: "lead"
      role: "coordinator"
    - name: "alice"
      role: "builder"
    - name: "bob"
      role: "builder"
```

Only the keys you include are overridden. Everything
else uses the defaults.

## All Settings

### Team

```yaml
team:
  name: "my-team"          # Team display name
  agents:                  # Agent list
    - name: "agent-name"   # Unique identifier
      role: "coordinator"  # coordinator or builder
```

Roles affect which governance rules apply. The
coordinator role matches `governance.checkout_approver_agent`
by default.

### Shifts

```yaml
shifts:
  duration_hours: 4        # Hours before refresh
  handoff_sentinel: "--- HANDOFF COMPLETE ---"
```

Shift duration controls how often agents get fresh
context. Shorter shifts reduce context degradation
but increase overhead from retros and restarts.

### Tasks

```yaml
tasks:
  lease_minutes: 15        # Lease before expiry
  initiative_interval: 3   # Tasks between proposals
```

The lease is renewed each time an agent produces an
artifact. If no artifact appears within the lease
window, the task expires.

The initiative interval triggers a self-directed
proposal every N completed tasks.

### Monitoring

```yaml
monitoring:
  default_window_minutes: 60   # Look-back window
  stale_threshold_polls: 3     # Polls before STALE
  excluded_files:              # Ignore these files
    - "bus-offsets.json"
    - "CLAUDE.md"
  excluded_extensions:
    - ".pyc"
    - ".lock"
```

The output clock checks for file modifications
within the look-back window. Excluded files are
infrastructure, not real output.

### Cron

```yaml
cron:
  poll_timeout_minutes: 15     # Heartbeat timeout
  meeting_timeout_minutes: 5   # Meeting poll timeout
  scheduler_timeout_minutes: 90
```

If an agent misses heartbeats for longer than the
timeout, it shows as EXPIRED in the watchdog.

### Bus

```yaml
bus:
  default_ttl_hours: 168       # Message TTL (1 week)
  snapshot_ttl_hours: 8760     # Snapshot TTL (1 year)
```

Expired messages are filtered out at read time
(lazy expiration). No messages are ever deleted
from the log files. Weekly rotation (`snapshot.py`)
archives old weeks but does not delete them.

### Governance

```yaml
governance:
  checkout_approver_agent: "coordinator"
  checkout_approval_window_minutes: 60
  checkout_keywords:
    - "checkout"
    - "wrap up"
```

Controls who can authorize agent checkout and what
phrases trigger checkout detection.

### PR Workflow

```yaml
workflow:
  max_pr_lines: 1000          # Max lines per PR
  min_reviewers: 2            # Required approvals
  privacy_scan: true          # Enable privacy gate
  privacy_patterns:           # Strings to scan for
    - "your-company"
    - "@your-domain"
  steps:                      # Review sequence
    - "privacy_scan"
    - "peer_review"
    - "open_pr"
    - "merge"
  permissions:                # Per-role access
    coordinator:
      open_pr: true
      review: true
      merge: true
    builder:
      open_pr: true
      review: true
      merge: true
```

The default workflow is a 4-step sequence. Add
custom steps by extending the `steps` list:

```yaml
# Example: add security review and CI
workflow:
  steps:
    - "privacy_scan"
    - "security_review"
    - "peer_review"
    - "open_pr"
    - "ci_check"
    - "merge"
```

The rules in `.claude/rules/pr-workflow.md` reference
these config values. Claude Code loads the rules
automatically when working in the repo.

### Paths

```yaml
paths:
  bus_root: "system/bus"
  cron_registry: "system/cron-registry.json"
  cache_dir: "system/cache"
  workspaces: "workspaces"
  defaults: "defaults"
  config: "config"
```

All paths are relative to `AGENT_OS_ROOT` (or the
repo root if unset). Change these if your deployment
layout differs from the default.

## Rules Override

Rules work the same way as config: defaults ship
with the repo, you override with your own.

```
defaults/rules/pr-workflow.md    <-- shipped
config/rules/pr-workflow.md      <-- your override
.claude/rules/pr-workflow.md     <-- merged (runtime)
```

Run `python3 setup.py init` to merge. The setup
script copies all files from `defaults/rules/`, then
overwrites with any matching files from `config/rules/`.
You can also add entirely new rules in `config/rules/`
that don't exist in defaults.

### Example: Override the PR workflow

```bash
mkdir -p config/rules
cp defaults/rules/pr-workflow.md config/rules/
# Edit config/rules/pr-workflow.md with your process
python3 setup.py init
```

Claude Code loads `.claude/rules/` automatically, so
your overridden rules take effect immediately in the
next session.

### Example: Add a custom rule

```bash
cat > config/rules/security-review.md << 'EOF'
# Security Review

All changes to scripts/ require security review
before merge. Check for command injection, path
traversal, and credential exposure.
EOF
python3 setup.py init
```

## CLI

```bash
# Show merged config
python3 scripts/config/loader.py

# Get a specific value
python3 scripts/config/loader.py --key tasks.lease_minutes

# Validate config
python3 scripts/config/loader.py --validate
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_OS_ROOT` | Repo root | Override root directory |

## Merge Rules

- **Dicts:** Merged recursively (key-by-key)
- **Lists:** Replaced entirely (not appended)
- **Scalars:** Overridden by user value

This means if you want to add an agent, you must
include the full agents list in your override.
There is no way to append to a list.
