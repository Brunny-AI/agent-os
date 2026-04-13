#!/usr/bin/env python3
"""Config loader with defaults/override merge.

Loads configuration from defaults/agent-os.yaml, then
merges any user overrides from config/agent-os.yaml.
User config only needs to contain the keys being changed.

The merge is recursive: nested dicts are merged key-by-key,
lists are replaced (not appended), and scalar values are
overwritten.

Usage as library:
    from scripts.config.loader import load_config
    cfg = load_config()
    ttl = cfg["bus"]["default_ttl_hours"]

Usage as CLI:
    python scripts/config/loader.py                # show merged
    python scripts/config/loader.py --key bus.root  # get one key
    python scripts/config/loader.py --validate      # check config
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _repo_root() -> str:
    """Resolve the repository root directory."""
    return os.environ.get(
        "AGENT_OS_ROOT",
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )


def _load_yaml(path: str) -> dict[str, object]:
    """Load a YAML file using only stdlib.

    Parses a subset of YAML sufficient for agent-os config:
    scalar values, nested mappings, and simple lists.
    Does NOT support anchors, tags, or multi-line strings.

    For full YAML support, install PyYAML (optional).
    """
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        pass

    return _parse_simple_yaml(path)


def _parse_simple_yaml(path: str) -> dict[str, object]:
    """Minimal YAML parser for flat/nested config files.

    Handles:
    - key: value (scalars)
    - key: (start of nested mapping)
    - - item (lists)
    - # comments
    - Indentation-based nesting (2-space)

    Does NOT handle:
    - Flow style ({}, [])
    - Multi-line strings (|, >)
    - Anchors (&, *)
    - Tags (!!)
    """
    result: dict[str, object] = {}
    stack: list[tuple[int, dict]] = [(-1, result)]

    with open(path) as f:
        lines = f.readlines()

    # Pre-scan: find keys whose children start with "-"
    # to distinguish lists from nested mappings
    list_parents: set[int] = set()
    for i, line in enumerate(lines):
        s = line.rstrip()
        if not s or s.lstrip().startswith("#"):
            continue
        if s.lstrip().startswith("- "):
            # Find the parent key above this indent
            line_indent = len(line) - len(line.lstrip())
            for j in range(i - 1, -1, -1):
                pline = lines[j].rstrip()
                if not pline or pline.lstrip().startswith("#"):
                    continue
                p_indent = len(lines[j]) - len(
                    lines[j].lstrip()
                )
                if p_indent < line_indent:
                    list_parents.add(j)
                    break

    current_list: list[object] | None = None
    list_indent = -1
    list_parent_line = -1

    for line_num, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Close finished list
        if (
            current_list is not None
            and indent <= list_indent
        ):
            current_list = None

        # Pop stack to find parent at correct indent
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        content = stripped.lstrip()

        # List item
        if content.startswith("- "):
            item_content = content[2:].strip()
            if current_list is not None:
                if ":" in item_content:
                    item_dict: dict[str, object] = {}
                    parts = item_content.split(":", 1)
                    k = parts[0].strip()
                    v = _parse_value(parts[1].strip())
                    item_dict[k] = v
                    current_list.append(item_dict)
                else:
                    current_list.append(
                        _parse_value(item_content)
                    )
            continue

        # Key: value
        if ":" in content:
            parts = content.split(":", 1)
            key = parts[0].strip()
            raw_val = parts[1].strip()

            _, parent = stack[-1]

            if raw_val == "" or raw_val.startswith("#"):
                if line_num in list_parents:
                    # This key starts a list
                    new_list: list[object] = []
                    parent[key] = new_list
                    current_list = new_list
                    list_indent = indent
                else:
                    # Nested mapping
                    child: dict[str, object] = {}
                    parent[key] = child
                    stack.append((indent, child))
            elif raw_val == "[]":
                parent[key] = []
            else:
                parent[key] = _parse_value(raw_val)

    return result


def _parse_value(raw: str) -> object:
    """Parse a YAML scalar value."""
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False
    if raw.lower() in ("null", "~", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _deep_merge(
    base: dict[str, object],
    override: dict[str, object],
) -> dict[str, object]:
    """Recursively merge override into base.

    Rules:
    - Dicts are merged recursively
    - Lists are replaced (not appended)
    - Scalars are overwritten

    Args:
        base: Default configuration.
        override: User overrides.

    Returns:
        Merged configuration dict.
    """
    merged = dict(base)
    for key, val in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(val, dict)
        ):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def load_config(
    root: str | None = None,
) -> dict[str, object]:
    """Load and merge configuration.

    Args:
        root: Repository root. Defaults to AGENT_OS_ROOT
            or auto-detected from script location.

    Returns:
        Merged configuration dict (defaults + user).
    """
    if root is None:
        root = _repo_root()

    defaults_path = os.path.join(
        root, "defaults", "agent-os.yaml"
    )
    config_path = os.path.join(
        root, "config", "agent-os.yaml"
    )

    if not os.path.exists(defaults_path):
        print(
            f"Warning: defaults not found at "
            f"{defaults_path}",
            file=sys.stderr,
        )
        defaults = {}
    else:
        defaults = _load_yaml(defaults_path)

    if os.path.exists(config_path):
        overrides = _load_yaml(config_path)
        if not isinstance(overrides, dict):
            print(
                f"Warning: config override at "
                f"{config_path} is not a mapping, "
                f"ignoring",
                file=sys.stderr,
            )
            config = defaults
        else:
            config = _deep_merge(defaults, overrides)
    else:
        config = defaults

    return config


def get_value(
    config: dict[str, object],
    dotted_key: str,
) -> object:
    """Get a value by dotted key path.

    Args:
        config: Configuration dict.
        dotted_key: Key path like "bus.root" or
            "tasks.lease_minutes".

    Returns:
        The value at the key path, or None if not found.
    """
    parts = dotted_key.split(".")
    current: object = config
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def validate_config(
    config: dict[str, object],
) -> list[str]:
    """Validate configuration for required fields.

    Returns:
        List of validation error messages (empty = valid).
    """
    errors: list[str] = []

    required_sections = [
        "team", "governance", "shifts", "tasks",
        "monitoring", "cron", "bus", "paths",
    ]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing section: {section}")

    if "schema_version" not in config:
        errors.append("Missing schema_version")
    elif config["schema_version"] != 1:
        errors.append(
            f"Unsupported schema_version: "
            f"{config['schema_version']}"
        )

    team = config.get("team", {})
    if isinstance(team, dict):
        agents = team.get("agents", [])
        if not agents:
            errors.append(
                "team.agents must have at least 1 agent"
            )

    return errors


def main() -> None:
    """CLI interface for config loader."""
    parser = argparse.ArgumentParser(
        description="Agent OS config loader"
    )
    parser.add_argument(
        "--key", help="Get specific key (dotted path)"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate configuration"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    args = parser.parse_args()

    config = load_config()

    if args.validate:
        errors = validate_config(config)
        if errors:
            for e in errors:
                print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        else:
            print("Configuration valid.")
        return

    if args.key:
        val = get_value(config, args.key)
        if val is None:
            print(
                f"Key not found: {args.key}",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.json:
            print(json.dumps(val, indent=2))
        else:
            print(val)
        return

    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
