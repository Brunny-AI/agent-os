## Summary
<!-- 1-3 bullet points describing what changed -->

## Internal Review Checklist

All items MUST be completed before opening this PR.
Replace [ ] with [x] and fill in artifact links.

### Privacy Scan
- [ ] Ran `grep -rnE` privacy scan (0 matches)
- [ ] No real names, emails, credentials, or
      company-specific paths in any changed file

### Adversarial Review
- [ ] Ran `/codex:adversarial-review` on the diff
- Review output: <!-- paste link or summary -->

### Peer Review
- [ ] Opened peer review meeting on bus
- Channel: <!-- e.g., meeting-review-{branch-name} -->
- [ ] At least 2 agents signed off

### Compliance
- [ ] Alex (CoS) reviewed for compliance issues
- Sign-off: <!-- Alex's bus message link or "N/A" -->

## Test Plan
- [ ] Privacy scan passes (pre-push hook)
- [ ] No direct commits to main (pre-commit hook)
- [ ] Changed files stay within 80-char line limit
