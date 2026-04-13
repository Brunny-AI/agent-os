# PR Workflow

Agent OS enforces a pull request workflow by default.
Customize the review steps in `config/agent-os.yaml`
under the `workflow` key.

## Core Rule
**No direct commits to main.** Enforced by
pre-commit hook (`scripts/hooks/pre-commit`).

## Change Size Limit
Every PR must be under **1000 lines changed**.
Override: `workflow.max_pr_lines` in config.

## Review Sequence

Every change follows this sequence. Steps can be
configured (enabled/disabled) in config but the
defaults enforce all of them.

### Step 1: Privacy Scan
Run the pre-push hook before every push:
```bash
bash scripts/hooks/pre-push
```
Or manually:
```bash
grep -rnE "your-company|@your-domain" . \
  --exclude-dir=.git \
  --exclude-dir=scripts/hooks
```
Catches real names, emails, credentials, and
company-specific references. Customize the pattern
in `config/agent-os.yaml` under `workflow.privacy_patterns`.

### Step 2: Peer Review
At least 2 agents (not including the author) must
review and approve. Use the meeting system for
structured review discussions.

How you run peer review is up to your team:
- Bus meeting channel (built-in)
- GitHub PR comments
- External review tools

Config: `workflow.min_reviewers` (default: 2)

### Step 3: Open Pull Request
Push branch and create PR. If using GitHub, the
template at `.github/pull_request_template.md`
provides a checklist.

### Step 4: Merge
Merge when review criteria are met. The pre-commit
hook prevents direct pushes to main regardless.

## Git Identity (per-commit)
```bash
git -c user.name="{agent}" \
  -c user.email="{agent}@example.com" \
  commit -m "[{agent}] verb: description"
```

## Branch Naming
```
{agent}/{description}
```

## Role Permissions

Roles are defined in your agent registry. Default
permissions:

| Action | coordinator | builder | reviewer |
|--------|------------|---------|----------|
| Open PR | Yes | Yes | No |
| Peer review | Yes | Yes | Yes |
| Approve + merge | Yes | Yes | No |

Override by defining `workflow.permissions` in config.

## Git Hooks

Installed automatically by `setup.py init`:
```bash
cp scripts/hooks/pre-commit .git/hooks/
cp scripts/hooks/pre-push .git/hooks/
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

## Extending the Workflow

Add custom review steps by creating rules in
`config/rules/` (not yet supported in MVP; use
`.claude/rules/` directly for now). Common additions:

- **Security review**: Add a step between privacy
  scan and peer review for security-sensitive changes
- **External CI**: Add GitHub Actions, Gemini Code
  Assist, or other automated reviewers as a step
- **Compliance gate**: Require coordinator sign-off
  on changes touching shared infrastructure
