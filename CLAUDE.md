# Agent OS

Open-source management system for AI agent teams.
Operational philosophy included.

## Languages

- **Python 3.10+** — Core scripts
- **Bash** — Shell scripts
- **Markdown** — Configuration, documentation

## Coding Standards

Key rules:

### Python
- 4-space indentation, 80 char line limit
- Google naming: `lower_with_under` for functions
  and variables, `CapWords` for classes
- Type annotations on all public APIs
  (use `X | None`, no bare `list`/`dict`)
- Google-style docstrings with Args/Returns/Raises
- No bare `except:`, no mutable default arguments
- Use f-strings for formatting
- Group imports: stdlib, third-party, local
- Import packages/modules only, not individual names

### Shell
- 2-space indentation, 80 char line limit
- Bash only (`#!/usr/bin/env bash`)
- Quote all variables: `"${var}"` not `$var`
- Use `local` for variables, `readonly` for constants
- Errors to STDERR (`>&2`), always check return values
- Use `"$@"` for passing arguments
- Scripts over 100 lines should be Python instead

## Documentation Accuracy

Only reference files, directories, and components
that actually exist in this repo. Do not document
planned or future features as if they are present.
Update CLAUDE.md and README.md as components are
added.

## Privacy (PUBLIC REPO)

This is a public repository. Every file is visible to the world.

- **No real names** — use `{agent}`, `{founder}`, role titles
- **No real email addresses** — use `{agent}@example.com`
- **No credential paths, SSH keys, or token references**
- **No company-specific internal tool names or workspace paths**
- **Pre-push check:**

```bash
grep -rnE "your-company|@your-domain" . \
  --exclude-dir=.git \
  --include="*.md" \
  --include="*.py" \
  --include="*.sh"
```

## Git Workflow

All changes go through pull requests. No direct commits to main.

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

1. Privacy scan (grep for private info before pushing)
2. Internal: automated adversarial review + peer review + compliance review
3. External: Gemini Code Assist auto-reviews on GitHub
4. Address feedback, then `/gemini review` to re-check
5. Merge when clean

## Architecture Principles

- **Plugin/extension support** — Core OS is generic.
  Company-specific configs live in private extensions.
- **File-based, no external deps** — No databases,
  no message queues. Local files only.
- **Anti-coasting by design** — Idle detection and
  productivity monitoring built in.
- **Shift boundaries** — Context refresh cycle with
  automatic retros and handoffs.
- **Peer monitoring** — Agents check each other's
  output, not just their own.
