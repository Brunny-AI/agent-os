# PR Workflow — Agent OS Public Repo

## Scope
This rule applies to the `agent-os` public GitHub repo (brunny-ai org). It does NOT apply to the internal `workspaces/` repo.

## Core Rule
**No direct commits to main.** Every change goes through a pull request with mandatory code review. No exceptions.

## Change Size Limit
Every PR must be under **1000 lines changed**. If a change exceeds this, split it into smaller PRs that can each be reviewed independently.

## Privacy Gate (MANDATORY — check BEFORE every PR)

**This is a public repo.** Every file in every PR is visible to the world. Before opening ANY PR, verify:

- **No real names** — use `{agent}`, `{founder}`, role titles only
- **No email addresses** — use `{agent}@example.com` as placeholder
- **No SSH paths, token paths, or credential references**
- **No company-specific tool references** (internal skills, workspace paths, bus channels)
- **No employer-adjacent content** (names of past/current employers)

Run this grep before pushing: `grep -rn "brunny\|@brunny\|scout@\|kai@\|dong@\|alex@\|derek@" . --include="*.md" --include="*.py" --include="*.sh" | grep -v .git`

If ANY match is found, fix it before proceeding. No exceptions.

## Code Review Pipeline

Every change follows this exact sequence. No steps may be skipped.

### Phase 1: Internal Review (before PR is opened)

1. **Privacy scan** (see Privacy Gate above)
   - Run the grep check
   - Fix all matches
   - This is non-negotiable for a public repo

2. **Automated adversarial review**
   - Run `/codex:adversarial-review` on the diff
   - Address all findings using `/address-feedback`
   - Do not proceed until Codex review is clean

3. **Peer review meeting**
   - Open a 1:1 meeting on the bus with:
     - One peer reviewer (whoever is NOT the author)
     - Compliance reviewer (mandatory for all changes)
   - Use `/meeting-guide` for the review meeting format
   - Both reviewers must confirm alignment before proceeding

### Phase 2: External Review (after PR is opened)

3. **Open pull request**
   - Push branch to agent-os repo using agent's SSH key (`github-scout` or `github-kai`)
   - Create PR with `gh pr create` — include summary of internal review
   - Use per-commit git identity: `git -c user.name="Scout" -c user.email="scout@brunny.ai"`

4. **Gemini Code Assist review**
   - Gemini Code Assist (Google's GitHub app) automatically reviews the PR
   - Address all Gemini feedback using `/address-feedback`
   - Push fixes to the same branch
   - After pushing fixes, request re-review by commenting `/gemini review` on the PR
   - Repeat until Gemini has no remaining issues (review state is clean)
   - Do NOT merge until Gemini's latest review has zero unresolved comments

5. **Merge**
   - Only **founder (dong)** or **Scout** may approve and merge
   - Merge to main only when Gemini's latest review is clean (no unresolved comments)
   - Internal review wins if it conflicts with Gemini's feedback

## Operational Details

### Git Identity (per-commit, never repo-level)
```bash
git -c user.name="Scout" -c user.email="scout@brunny.ai" commit -m "message"
```

### SSH Push
```bash
GIT_SSH_COMMAND="ssh -F /Users/brunny-ai-dong-chen/.ssh/config" git push origin branch-name
```

### GH CLI (always use GH_TOKEN from workspace)
```bash
GH_TOKEN=$(cat workspaces/scout/.ssh/gh-token) gh pr create --repo Brunny-AI/agent-os ...
GH_TOKEN=$(cat workspaces/scout/.ssh/gh-token) gh pr merge N --squash ...
```

### Request Gemini Re-review After Fixes
```bash
GH_TOKEN=$(cat workspaces/scout/.ssh/gh-token) gh pr comment N --body "/gemini review"
```

### Repo Location
`projects/agent-os/` (cloned from `github-scout:Brunny-AI/agent-os.git`)

## Who Can Do What

| Action | Founder | Scout | Kai | Alex | Derek |
|--------|---------|-------|-----|------|-------|
| Open PR | Yes | Yes | Yes | No | No |
| Review (internal peer) | Yes | Yes | Yes | No | No |
| Review (compliance) | No | No | No | Yes | No |
| Approve + merge | Yes | Yes | No | No | No |

## Branch Naming
Use: `{agent}/{description}` (e.g., `scout/port-event-bus`, `kai/add-quickstart`)

## Architecture Constraint
The agent-os repo must support a **plugin/extension system** from day one. Company-specific configurations, credentials, and content pipelines live in private extensions, not in the core repo. Design every component to be extensible.

## Convergence Plan
When all OS components are ported and the plugin system works, the internal codebase converges to: `agent-os (public core) + brunny-extension (private)`. The trigger is a milestone decision by the founder.
