# Contributing to agent-os

Setup walkthrough for external contributors.

## TL;DR — your first contribution in 10 minutes

```bash
git clone https://github.com/Brunny-AI/agent-os.git
cd agent-os
python3 setup.py init
bash examples/quickstart/run-demo.sh
```

You now have a working 3-agent team running locally. Make a change, open a PR, the 5-step pipeline guides the rest.

## Prerequisites

- Python 3.10+ and Bash
- Git + a GitHub account
- That's it. Zero external dependencies (no databases, no message queues, no cloud services).

## Step 1 — Fork + clone

```bash
# On GitHub: click "Fork" on Brunny-AI/agent-os
git clone https://github.com/{your-handle}/agent-os.git
cd agent-os
git remote add upstream https://github.com/Brunny-AI/agent-os.git
```

(Use SSH if you prefer; HTTPS shown for the no-setup-needed default.)

## Step 2 — Run the demo

This is the fastest "does it work?" check:

```bash
python3 setup.py init
bash examples/quickstart/run-demo.sh
```

Expected: ~5 seconds wall-clock. You'll see all 7 MVP components run end-to-end (task engine, event bus, cron manager, output clock, v4.6 active-task gate, et al.). If any step fails, that's the bug to file as your first issue.

## Step 3 — Run the test suite

```bash
python3 -m unittest discover tests/
```

A few dozen tests, well under 5 seconds on a laptop. All should pass. If any fail on `main`, file an issue before opening a PR — you may have hit a real regression worth flagging separately.

## Step 4 — Make your first change

Pick something small for the first PR:

- Fix a typo in a doc.
- Add a missing edge case to an existing test.
- Improve an error message.

Avoid scope-creep on first contributions. Smaller PRs review faster and build the feedback-loop confidence.

```bash
git checkout -b {your-handle}/{short-description}
# ... make changes ...
python3 -m unittest discover tests/  # verify tests still pass
git commit -m "[{your-handle}] verb: description"
git push -u origin {your-handle}/{short-description}
gh pr create  # uses the .github/pull_request_template.md
```

## Step 5 — The 5-step PR pipeline

Every PR (yours and ours) goes through:

1. **Pre-push hook** — local privacy scan blocks credential/path leaks (`scripts/hooks/pre-push`).
2. **Adversarial review** — internal we use `/codex:adversarial-review`; external you can use any code-review process you like, but DO read your own diff once with fresh eyes before opening.
3. **Peer review** — for external contributors, the `Code Owner APPROVE` step covers this. For internal agents, an explicit bus channel sign-off is required (irrelevant to your fork).
4. **Open PR + Gemini auto-fires** — Gemini Code Assist comments automatically. `/gemini review` does NOT auto-re-fire on push; comment it manually after every push to re-trigger.
5. **Code Owner APPROVE** — a maintainer (currently `@brunny-scout` or `@brunny-kai`) reviews + approves.

Auto-merge: `gh pr merge --auto --squash --delete-branch` from the author. Fires when CO APPROVE + all required checks green + no commits since approval (stale reviews dismissed by ruleset).

## Step 6 — Common pitfalls

These will save you a debug round:

- **Run from a fresh state.** If you've previously run `setup.py init` in a different repo or with different config, `system/` and `workspaces/` may be stale. Recover with `rm -rf system workspaces && python3 setup.py init`. Stale state is the most common cause of "missing bus channel" errors during the demo — try the recovery before assuming the demo is broken.
- **`npm ci` requires `package-lock.json`.** Not relevant to agent-os core (Python+Bash), but if you're contributing to the JS/Astro side of any companion site (warren, brief), generate the lockfile locally before push.
- **Stacked PRs:** if PR A is the dependency of PR B, Gemini reads B against `main` (not against A's branch). It WILL flag B's correct-vs-post-A code as "critical." Code Owners reason about the dep chain before forwarding such findings — but you should call out the dependency in your PR description so reviewers have context.
- **PR size budget: 1000 lines.** Excludes lockfiles, but counts everything else. If you're at 800+ lines, consider splitting.
- **Auto-merge does NOT auto-rebase** under strict status policy. If your PR sits BLOCKED + BEHIND main for >10 min, manually rebase + force-push.

## Step 7 — Style guide

`.gemini/styleguide.md` is the source of truth for code style. Highlights:

### Python
- 4-space indent, 80 char line limit
- Module-only imports (`import datetime`, not `from datetime import ...`)
- `dict[str, Any]` annotations (parameterize generics)
- Google-style docstrings with `Args:`/`Returns:`/`Raises:`
- Sort imports lexicographically within groups (stdlib, third-party, local)

### Bash
- 2-space indent, 80 char line limit
- Quote all variables: `"${var}"` not `$var`
- Errors to STDERR (`>&2`)
- Use `local`/`readonly` appropriately

ESLint catches some, the pre-commit hook catches more (`scripts/hooks/check_imports.py` enforces module-only imports), and Gemini catches the rest in PR review.

## What we're looking for

In rough priority order:

1. **Bug reports + fixes.** Reproducible bugs with a failing test that gets fixed are the highest-value PRs.
2. **Documentation improvements.** Did you hit a confusing step in this doc? Fix it.
3. **New examples in `examples/`.** A new agent-os usage pattern (e.g., a custom skill, a new cron pattern) helps the next user.
4. **Test coverage.** Add tests for paths that aren't covered yet.

What we're NOT looking for (yet):

- Net-new MVP components. The 7 MVP components are intentional. New components need a design discussion first — open an issue with the use case.
- External dependency additions. Zero-deps is a feature, not an oversight.
- Rewrites of working code without a measurable improvement claim.

## Questions

- Open a GitHub issue for bugs or feature discussion.
- For real-time questions, hit any of the maintainers on their public profile.

## Code of conduct

Be kind. Disagree on substance, not on people. We're all here to make multi-agent operations less painful for everyone.

Welcome aboard.
