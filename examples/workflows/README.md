# Workflow Examples

Agent OS ships with a minimal 4-step PR workflow:
privacy scan, peer review, open PR, merge.

Most teams need more. These examples show how to
extend the workflow for common scenarios.

## How to Use

Copy the relevant YAML into your `config/agent-os.yaml`.
Only include the keys you want to override.

## Available Examples

### `enterprise.yaml`
Full review pipeline with security review, compliance
gate, and external CI integration. Good for teams
that need audit trails and multi-layer review.

Steps: privacy scan, security review, peer review,
compliance gate, open PR, external CI, merge.

### `minimal.yaml`
Relaxed workflow for solo developers or small teams.
Reduces reviewer count and removes the privacy scan
(useful for private repos).

Steps: peer review, open PR, merge.
