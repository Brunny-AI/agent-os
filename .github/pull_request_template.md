## Summary
<!-- 1-3 bullet points describing what changed -->

## Internal Review Checklist (pre-push)

All items MUST be completed before opening this PR.
Replace [ ] with [x] and fill in artifact links.

### Privacy Scan
- [ ] Ran `bash scripts/hooks/pre-push` (passed)
- [ ] No real names, emails, credentials, or
      company-specific paths in any changed file

### Adversarial Review
- [ ] Ran `/codex:adversarial-review` on the diff
- Review output: <!-- paste link or summary -->

### Peer Review (2 bus sign-offs)
- [ ] Branch pushed to origin before requesting review
      (show-bytes rule: reviewer must see actual bytes,
      not a verification claim)
- [ ] Opened peer review on bus
- Channel: <!-- e.g., review-{branch-name} -->
- [ ] Sign-off 1: <!-- agent + bus message link -->
- [ ] Sign-off 2: <!-- agent + bus message link -->

### Compliance (if touching shared infra)
- [ ] Alex (CoS) reviewed for compliance issues
- Sign-off: <!-- Alex's bus message link or "N/A" -->

## Auto-Merge (post-open)

- [ ] Enabled auto-merge via
      `gh pr merge --auto --squash --delete-branch`
      (defaults to current branch's PR; fires automatically
      when Code Owner APPROVE + all required checks clear)

## Post-Open Gates (Gemini + Step 6)

These happen AFTER the PR is open. Auto-merge waits on them.

### Step 5: Gemini auto-review
- GitHub triggers automatically on PR open / new push.
- If silent for >2 min post-push: comment `/gemini review` to nudge.
- Author addresses every finding (fix commit OR reply with reasoning).
- No "Gemini unresponsive" dismissals.

### Step 6: Code Owner verification (mandatory)
- Non-author Code Owner reviews the diff and Gemini feedback.
- Verifies Gemini's findings were addressed at class level (not
  just line-item silenced).
- Posts APPROVE on GitHub (required by branch protection).
- Routing:
  - Scout author → Kai verifies
  - Kai author → Scout verifies
  - Founder/Alex author → Scout or Kai verifies

## Test Plan
- [ ] `bash scripts/hooks/pre-push` passes (privacy)
- [ ] Line-length within repo limits (Python/Shell/YAML: 80 chars)
- [ ] If touching shell: `bash -n <file>` passes
- [ ] If touching Python:
      `python3 -c "import ast; ast.parse(open('<file>').read())"`
      passes (matches pre-commit hook pattern; no `__pycache__/`
      side effect from `py_compile`)
- [ ] If touching config:
      `python3 -c "import yaml; yaml.safe_load(open('<file>'))"`
      passes (`safe_load` accepts a file object directly — no
      `.read()` needed)
- [ ] CI workflow checks (post-open): Privacy scan, Shellcheck,
      PR size, Unit tests, CodeQL Analyze (python + actions)
