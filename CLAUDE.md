# Agent OS

Configurable framework for running multi-agent
Claude Code teams. Operational philosophy included.

## What This Is

- **For:** Claude Code users who want multi-agent
  operations without building coordination plumbing
- **Runtime:** Claude Code + Python 3.10+ + Bash + Unix
- **Dependencies:** Zero external. No databases, no
  message queues, no cloud services.
- **License:** MIT

## MVP Components (7)

1. Event Bus (agent messaging, JSONL, peek/commit)
2. Cron Manager (scheduling, heartbeats, watchdog)
3. Task Engine (work queue, 15-min leases)
4. Output Clock (filesystem-based idle detection)
5. Meeting System (round-based with challenges)
6. Agent Registry (team definition)
7. Shift Manager (4h context refresh lifecycle)

Not in MVP: Skill System (v2).

## Repository Structure

```
defaults/          # Read-only shipped defaults
  rules/           # Default rules (source of truth)
config/            # User overrides (gitignored)
  rules/           # Rule overrides (gitignored)
scripts/           # Core OS scripts
examples/          # Ready-to-run team configs
docs/              # Architecture and guides
setup.py           # python3 setup.py init
```

Runtime dirs (gitignored, created by setup):
- `system/` (bus channels, receipts, cron registry)
- `workspaces/` (per-agent state, logs, memory)
- `.claude/rules/` (merged from defaults + config)

## Rules

Rules are shipped in `defaults/rules/` and merged
into `.claude/rules/` by `setup.py init`. Override
any rule by placing a file with the same name in
`config/rules/`. Claude Code loads the merged result.

Default rules:

| Rule | What it governs |
|------|----------------|
| `architecture.md` | MVP scope, components, modes |
| `design-constraints.md` | Dependencies, formats, concurrency |
| `privacy-boundary.md` | What's public vs private |
| `implementation-phases.md` | Build order, PR rules |
| `pr-workflow.md` | PR process, review pipeline |

## Languages

- **Python 3.10+** for core scripts
- **Bash** for shell scripts
- **Markdown** for config, documentation

## Coding Standards

Key rules:

### Python
- 4-space indentation, 80 char line limit
- Google naming: `lower_with_under` for modules,
  packages, functions, methods, and variables;
  `CapWords` for classes; `CAPS_WITH_UNDER` for
  constants
- Type annotations on all public APIs (use `X | None`,
  specify type parameters for generic types)
- Google-style docstrings with Args/Returns/Raises
- No bare `except:`, no mutable default arguments
- Module-level docstrings required; no relative imports
- Use f-strings for formatting
- Sort imports lexicographically within groups:
  stdlib, third-party, local
- Import packages/modules only, not individual names

### Shell
- 2-space indentation, 80 char line limit
- Bash only (`#!/usr/bin/env bash`)
- Quote all variables: `"${var}"` not `$var`
- Use `local` for variables, `readonly` for constants
  (`UPPERCASE_WITH_UNDERSCORES`)
- Errors to STDERR (`>&2`), always check return values
- Use `"$@"` for passing arguments
- Function header comments for non-trivial functions
- Scripts over 100 lines should be Python instead

## Documentation Accuracy

Only reference files, directories, and components
that actually exist in this repo. Do not document
planned or future features as if they are present.
Update CLAUDE.md and README.md as components are
added.

## Privacy (PUBLIC REPO)

This is a public repository. Every file is visible
to the world. See `.claude/rules/privacy-boundary.md`
for the full policy.

- **No real names** -- use `{agent}`, `{founder}`
- **No real emails** -- use `{agent}@example.com`
- **No credentials, SSH keys, or token references**
- **No company-specific paths or tool names**
- **Pre-push check:**

```bash
grep -rnE "your-company|@your-domain" . \
  --exclude-dir=.git --exclude-dir=scripts/hooks
```

## Git Workflow

All changes go through pull requests. No direct
commits to main.

```bash
git checkout -b {agent}/{description}
git -c user.name="{agent}" \
  -c user.email="{agent}@example.com" \
  commit -m "[{agent}] add: description" \
  -m "Now possible: next step"
git push -u origin {agent}/{description}
gh pr create
```

## PR Review Pipeline

1. Privacy scan (grep for private info)
2. Internal review (Alex compliance check)
3. Gemini Code Assist auto-review on GitHub
4. Address feedback, `/gemini review` to re-check
5. Merge when clean

## Key Design Decisions

- **Override-based config:** users customize via
  `config/`, core files stay untouched
- **Monolith with defaults:** one command gets a
  working 3-agent team, complexity hidden
- **Philosophy as defaults:** anti-coasting, idle
  detection, shift boundaries are on by default,
  tunable via config
- **Convergence:** public repo IS the production
  runtime. No internal fork.
- **Fresh installs only:** MVP does not support
  in-place upgrades. schema_version in all files
  for future migration.
