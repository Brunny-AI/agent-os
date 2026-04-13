# Architecture Decisions

## Product Definition
- Agent OS is a configurable, opinionated framework for
  running multi-agent Claude Code teams
- Target audience: Claude Code starter users who want
  multi-agent ops without building plumbing
- Runtime: Claude Code on Python 3.10+ / Bash / Unix
- Not LLM-agnostic. No Windows in MVP.
- Dependencies: Python, Bash, shared filesystem,
  Claude Code. No databases, no message queues,
  no cloud services.

## MVP Components (7 of 9)
Ship these in MVP:
1. Event Bus (agent-bus/)
2. Cron Manager (cron-manager/)
3. Task Engine (task-engine.py)
4. Output Clock (output-clock.py)
5. Meeting System (meeting/)
6. Agent Registry (config/registry.yaml)
7. Shift Manager (shift-manager/)

Deferred to v2:
- Skill System (modular capabilities)
- Rule System (path-scoped enforcement)

Do NOT build v2 components. Do NOT add features
beyond these 7. If something requires Skill System
or Rule System, it waits.

## Default Example
- 3-agent team: Coordinator (CoS) + 2 Builders
- Demo task: agents build something together
  (e.g., CLI tool) with task division + peer review
- Must demonstrate all 7 components within 5 minutes

## Two Setup Modes
- Interactive: manual Claude Code sessions, no
  auto-restart, good for demos
- Autonomous: agent-loop.sh wrapper, watchdog,
  shift refresh, full lifecycle
- Do NOT promise autonomous behavior from
  interactive mode

## Configuration: Override-Based
- Core ships defaults/ (read-only)
- User customizes via config/ (override)
- Merge order: defaults < user config
- Scripts read merged config, never defaults directly
- User never edits core files
- Override system is per-version, NOT an upgrade path

## Runtime State Boundary
- system/ and workspaces/ are RUNTIME dirs
- Created by setup.py, listed in .gitignore
- NEVER shipped in the repo
- NEVER committed to version control
- Source tree contains ONLY immutable product code

## Schema Versioning
- All config and state files: schema_version field
- Increment on breaking changes
- MVP: fresh installs only, no in-place upgrades
- Migration tooling is v2

## Convergence Principle
The public repo IS the future production runtime.
- No internal-only features in MVP scope
- No internal fork. Bugs fixed in public repo.
- Every PR dogfooded: does it work for us?
- Private extension: ONLY config, credentials,
  company content
