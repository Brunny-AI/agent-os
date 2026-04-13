# Implementation Phases

Work proceeds in this order. Do not skip phases.
Do not start a later phase until the current phase
is complete and merged.

## Phase 1: Core Porting (3-5 PRs)
1. Event bus scripts (send, read, new-channel, status)
2. Cron manager (cron-manager.sh, watchdog, recovery,
   shift-refresh, agent-loop, fast-startup)
3. Task engine + output clock
4. Meeting system templates and helpers

Each PR: port from internal, genericize (remove
Brunny-specific references), add defaults/ config,
verify privacy boundary, test standalone.

## Phase 2: Config Layer (2-3 PRs)
5. Config loader (defaults + user override merge)
6. Templatize prompts with config variables
7. setup.py (scaffold workspaces, validate config,
   create bus channels)

## Phase 3: Default Example + Docs (2-3 PRs)
8. 3-agent team example with README
9. Architecture docs, config guide, extending guide
10. GitHub Action for privacy scanning (if needed)

## Phase 4: Polish + Launch
11. End-to-end testing (clone, setup, run, observe)
12. README with quickstart
13. Show HN preparation

## PR Rules
- Under 1000 lines per PR
- Privacy scan before every push
- Peer review per `.claude/rules/pr-workflow.md`
- Each PR must work standalone (no broken states
  between PRs)

## What NOT to build
- Windows support
- LLM-agnostic runtime
- pip-installable package
- Web UI or dashboard
- External API endpoints
- Content pipeline (Brief, Rednote, Bluesky)
- Banking or financial operations
- Any v2 component (Skill System, Rule System)
