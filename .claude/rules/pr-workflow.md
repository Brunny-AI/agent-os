# PR Workflow

## Scope
Applies to the agent-os public repo. Every change
goes through a pull request. No exceptions.

## Core Rule
**No direct commits to main.** Enforced by
pre-commit hook (`scripts/hooks/pre-commit`).

## Change Size Limit
Every PR must be under **1000 lines changed**.

## Privacy Gate (MANDATORY before every push)

This is a public repo. Every file is visible.
Enforced by pre-push hook (`scripts/hooks/pre-push`).

- **No real names** of any person
- **No email addresses** (use `{agent}@example.com`)
- **No SSH paths, token paths, or credentials**
- **No company-specific tool references**

## Internal Review Sequence

Every change follows this exact sequence.
No steps may be skipped. (INC-009 fix)

### Step 1: Privacy Scan
Run the pre-push hook manually:
```bash
grep -rnE "your-company|@your-domain" . \
  --exclude-dir=.git \
  --exclude-dir=scripts/hooks
```
Fix all matches before proceeding.

### Step 2: Adversarial Review
Run `/codex:adversarial-review` on the diff.
Address all findings using `/address-feedback`.
Do not proceed until review is clean.

### Step 3: Peer Review Meeting (MANDATORY)
Open a review meeting on the bus. This step cannot
be skipped or replaced by founder approval alone.
Require sign-off from at least 2 agents (not
including the author). Every code change gets
reviewed by teammates in a meeting before any PR
is opened. Record the meeting channel in the PR
template. Founder directive: "make sure all future
code changes review with them in an internal
meeting."

### Step 4: Open Pull Request
Push branch and create PR using the template at
`.github/pull_request_template.md`. All checklist
items must be filled with artifact links.

### Step 5: External Review
Gemini Code Assist auto-reviews on GitHub. Address
feedback, then `/gemini review` to re-check.
Merge when clean.

## Git Identity (per-commit)
```bash
git -c user.name="{agent}" \
  -c user.email="{agent}@example.com" \
  commit -m "[{agent}] verb: description"
```

## Branch Naming
Use: `{agent}/{description}`
(e.g., `scout/port-event-bus`)

## Who Can Do What

| Action | Founder | Builder | CoS |
|--------|---------|---------|-----|
| Open PR | Yes | Yes | No |
| Peer review | Yes | Yes | Yes |
| Compliance review | No | No | Yes |
| Approve + merge | Yes | Yes | No |

## Git Hooks (install after clone)
```bash
cp scripts/hooks/pre-commit .git/hooks/
cp scripts/hooks/pre-push .git/hooks/
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

`setup.py init` installs these automatically.

## Architecture Constraint
The repo must support a plugin/extension system.
Company-specific config lives in private extensions,
not in the core repo.
