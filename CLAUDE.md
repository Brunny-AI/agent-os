# Agent OS

Open-source management system for AI agent teams. Operational philosophy included.

## Project Structure

```
agent-os/
  .claude/          # Claude Code configuration
  .gemini/          # Gemini Code Assist style guide
  agents/           # Agent workspaces (one per agent)
  skills/           # Modular capabilities (SKILL.md specs)
  rules/            # Always-loaded behavioral rules
  docs/             # Documentation (playbook, quickstart)
  scripts/          # Core infrastructure scripts
```

## Languages

- **Python 3.10+** — Core scripts (event bus, cron manager, output clock, task engine)
- **Bash** — Shell scripts (startup, heartbeat, watchdog)
- **Markdown** — Configuration, skills, rules, documentation

## Coding Standards

Follow `.gemini/styleguide.md` for all code. Key rules:

### Python
- 4-space indentation, 80 char line limit
- Google naming: `lower_with_under` for functions/variables, `CapWords` for classes
- Type annotations on all public APIs
- Google-style docstrings with Args/Returns/Raises sections
- No bare `except:`, no mutable default arguments

### Shell
- 2-space indentation, 80 char line limit
- Bash only (`#!/usr/bin/env bash`)
- Quote all variables: `"${var}"` not `$var`
- Errors to STDERR (`>&2`), always check return values
- Scripts over 100 lines should be Python instead

## Build & Test

```bash
# No build step required. Pure Python + Bash.

# Run tests (when available)
python3 scripts/test_*.py
```

## Git Workflow

All changes go through pull requests. No direct commits to main.

```bash
# Create branch
git checkout -b {agent}/{description}

# Commit with agent identity
git -c user.name="{Agent}" -c user.email="{agent}@example.com" commit -m "message"

# Push and open PR
git push -u origin {branch}
gh pr create
```

## PR Review Pipeline

1. Internal: automated adversarial review + peer review + compliance review
2. External: Gemini Code Assist auto-reviews on GitHub
3. Address feedback, then `/gemini review` to re-check
4. Merge when clean

## Architecture Principles

- **Plugin/extension support** — Core OS is generic. Company-specific configs live in private extensions.
- **File-based, no external deps** — Event bus, task engine, cron manager all use local files. No databases, no message queues.
- **Anti-coasting by design** — Every component includes idle detection and productivity monitoring.
- **Shift boundaries** — 4-hour context refresh cycle with automatic retros and handoffs.
- **Peer monitoring** — Agents check each other's output, not just their own.

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Event Bus | `scripts/agent-bus/` | Inter-agent messaging (channels, peek/commit, receipts) |
| Cron Manager | `scripts/cron-manager/` | Poll scheduling, heartbeats, watchdog, shift boundaries |
| Output Clock | `scripts/output-clock.py` | Anti-coasting detection, idle diagnosis |
| Task Engine | `scripts/task-engine.py` | Work queue with leases, blockers, fallback chains |
| Skill System | `skills/` | Modular capabilities with SKILL.md specs |
| Meeting System | `skills/meeting-guide/` | Structured async meetings with mandatory challenges |
