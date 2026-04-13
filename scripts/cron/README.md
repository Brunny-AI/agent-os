# Cron Manager

Heartbeat-based cron job registry for cross-agent liveness
monitoring. No external dependencies.

## Quick Start

```bash
# Register a poll job
python3 scripts/cron/manager.py register alice poll JOB123

# Send heartbeat
python3 scripts/cron/manager.py heartbeat alice poll

# Check liveness status
python3 scripts/cron/manager.py status

# List all registered jobs
python3 scripts/cron/manager.py list

# Clean up expired meeting jobs
python3 scripts/cron/manager.py cleanup

# Checkout (requires approver authorization on bus)
python3 scripts/cron/manager.py checkout alice

# Trigger shift refresh (after writing handoff)
bash scripts/cron/shift_refresh.sh alice "4h boundary"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `manager.py` | Registry: register, heartbeat, status, list, cleanup, checkout |
| `shift_refresh.sh` | Write atomic flag for sidecar to trigger session restart |

## Design

- **Registry**: JSON file at `system/cron-registry.json`
- **Liveness**: heartbeat timestamps with configurable timeouts
- **Concurrency**: flock + atomic writes (temp file + os.replace)
- **Checkout gate**: searches bus for approver authorization
- **Shift refresh**: atomic flag file for sidecar detection

## Job Types

| Type | Timeout | Cadence |
|------|---------|---------|
| poll | 15 min | every 5 min |
| meeting | 5 min | every 1 min |
| scheduler | 90 min | every 60 min |

## Configuration

Set `AGENT_OS_ROOT` environment variable to override the
default repository root detection. The checkout approver
can be configured in `config/agent-os.yaml`:

```yaml
governance:
  checkout_approver_agent: "founder"
```
