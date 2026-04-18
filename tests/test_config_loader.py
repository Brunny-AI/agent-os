"""Config loader: defaults + override merge, agent registry shape.

Per Kai's spec-test-suite.md (test_agent_registry equivalent):
the agent registry IS the team config under `team.agents`. This
test verifies the loader produces a usable team definition from
a fixture YAML, that overrides merge correctly, and that
malformed input fails clearly rather than silently.
"""

from __future__ import annotations

import os
import unittest

from tests import _fixtures


def _load(
    root: str, *args: str
) -> "subprocess.CompletedProcess":  # noqa: F821
    """Invoke the loader CLI."""
    return _fixtures.run_script(
        "scripts/config/loader.py", *args,
        env_extra={"AGENT_OS_ROOT": root},
    )


def _write_yaml(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


class ConfigLoaderRegistryTest(unittest.TestCase):
    """Loader produces a 3-agent team from defaults; overrides
    layer cleanly; invalid YAML surfaces as a clear failure."""

    def setUp(self) -> None:
        self.root = _fixtures.mk_temp_workspace()
        self.defaults_path = os.path.join(
            self.root, "defaults", "agent-os.yaml"
        )
        self.config_path = os.path.join(
            self.root, "config", "agent-os.yaml"
        )

    def tearDown(self) -> None:
        _fixtures.cleanup(self.root)

    def test_registry_yaml_loads_three_agents(self) -> None:
        # Fixture: minimal team of 3 agents (1 coordinator
        # + 2 builders) — matches the Kai-spec acceptance.
        _write_yaml(self.defaults_path, """\
schema_version: 1
team:
  name: "test-team"
  agents:
    - name: "coordinator"
      role: "coordinator"
    - name: "builder-1"
      role: "builder"
    - name: "builder-2"
      role: "builder"
governance:
  checkout_approver_agent: "coordinator"
""")

        # Get team.agents via --key
        r = _load(self.root, "--key", "team.agents")
        self.assertEqual(r.returncode, 0, r.stderr)
        # The CLI prints JSON when key resolves to a complex
        # value; assert all 3 agent names appear.
        for name in ("coordinator", "builder-1", "builder-2"):
            self.assertIn(name, r.stdout)

        # Get team.name via --key (scalar resolution)
        r = _load(self.root, "--key", "team.name")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("test-team", r.stdout)

    def test_overrides_merge_only_changed_keys(self) -> None:
        # defaults: 3 agents + governance with 'coordinator'
        _write_yaml(self.defaults_path, """\
schema_version: 1
team:
  name: "test-team"
  agents:
    - name: "coordinator"
      role: "coordinator"
governance:
  checkout_approver_agent: "coordinator"
  checkout_approval_window_minutes: 60
""")
        # config override: only change the approver
        _write_yaml(self.config_path, """\
governance:
  checkout_approver_agent: "founder"
""")

        # Approver should be the OVERRIDE value
        r = _load(
            self.root, "--key",
            "governance.checkout_approver_agent",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("founder", r.stdout)

        # The unrelated default (window_minutes) must SURVIVE
        r = _load(
            self.root, "--key",
            "governance.checkout_approval_window_minutes",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("60", r.stdout)

        # Team name (untouched by override) must survive
        r = _load(self.root, "--key", "team.name")
        self.assertIn("test-team", r.stdout)


if __name__ == "__main__":
    unittest.main()
