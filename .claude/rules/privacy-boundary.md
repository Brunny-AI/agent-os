# Privacy Boundary (PUBLIC REPO)

## Must NEVER appear in this repo
- Real names of founders, employees, or users
- Real email addresses (use {agent}@example.com)
- SSH keys, API tokens, credential file paths
- Company-specific tool names or workspace paths
- Employer names or employer-adjacent terms
- Internal communication history or bus messages
- Hardcoded Google Drive, Dropbox, or cloud paths
- Specific revenue, user counts, or financial data

## Must appear genericized
- Operational philosophy (anti-coasting, shifts,
  meetings) with placeholder variables
- Component scripts with configurable parameters
- Default templates using {agent}, {founder},
  {team-name} placeholders
- Example configs with fictional team names

## Enforcement
- Pre-push grep documented in CLAUDE.md
- Alex (CoS) reviews every commit
- Contributors run privacy scan before opening PR:
  ```bash
  grep -rnE "your-company|@your-domain" . \
    --exclude-dir=.git \
    --exclude-dir=scripts/hooks
  ```
- config/ directory is gitignored (user data)
- system/ and workspaces/ are gitignored (runtime)

## Config vs Core boundary
- config/ = private (gitignored, user-maintained)
- defaults/ = public (shipped, read-only)
- scripts/ = public (shipped, read-only)
- system/ = private (runtime, gitignored)
- workspaces/ = private (runtime, gitignored)
