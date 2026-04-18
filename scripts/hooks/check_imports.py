#!/usr/bin/env python3
"""Pre-commit lint: enforce top-level stdlib imports (rule 19).

Reads Python source from stdin, AST-parses it, and flags any
`from X import Y` for stdlib X — except for two pragmatic
exemptions where the form is ubiquitous and the rule's
spirit (avoid namespace pollution + keep grep-discoverable
qualified names) doesn't apply:

- `from __future__ import ...` (language feature)
- `from typing import ...` (Google's own style allows it)

Usage:
    git show ":path/to/file.py" \\
      | python3 scripts/hooks/check_imports.py path/to/file.py

Exit code: 0 if clean, 1 if violations.

Why this exists: the same `from X import Y` style fix landed
in PR #24 R1, PR #29 R1, and PR #30 R1 — three rounds of the
same drift. Catching it locally before push removes the round
entirely.
"""

from __future__ import annotations

import ast
import sys


# Stdlib modules where `from X import Y` triggers the rule.
# Conservative list — only modules we've actually drifted on
# in past PRs, plus close neighbors. Easier to extend than
# to defend an over-aggressive baseline.
_STDLIB_MODULES = frozenset({
    "argparse",
    "datetime",
    "fcntl",
    "glob",
    "importlib",
    "io",
    "json",
    "os",
    "pathlib",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "tempfile",
    "time",
})

# Modules where `from X import Y` is the convention and the
# rule explicitly does not apply.
_EXEMPT_MODULES = frozenset({
    "__future__",
    "typing",
})


def _module_root(name: str | None) -> str:
    """Return the top-level package of a dotted import.

    e.g. 'os.path' → 'os'. None safe-defaults to ''.
    """
    if not name:
        return ""
    return name.split(".", 1)[0]


def find_violations(source: str) -> list[tuple[int, str]]:
    """Return [(lineno, message), ...] for stdlib `from X import`.

    Args:
        source: Python source code (as it would appear on disk
            or in the staged index).

    Returns:
        One entry per violating ImportFrom statement. Empty
        list when the file is clean.

    Raises:
        SyntaxError: from ast.parse if the source is invalid.
            Caller is responsible for catching (the syntax
            check elsewhere in pre-commit handles this case).
    """
    tree = ast.parse(source)
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        # `from . import x` (level > 0) — relative; skip.
        if node.level and node.level > 0:
            continue
        root = _module_root(node.module)
        if not root:
            continue
        if root in _EXEMPT_MODULES:
            continue
        if root in _STDLIB_MODULES:
            names = ", ".join(
                a.name for a in (node.names or [])
            )
            msg = (
                f"line {node.lineno}: "
                f"`from {node.module} import {names}` — use "
                f"`import {node.module}` (rule 19; stdlib "
                f"modules must be imported, not their "
                f"individual names)"
            )
            violations.append((node.lineno, msg))
    return violations


def main() -> int:
    """Read stdin, lint, return exit code."""
    if len(sys.argv) < 2:
        print(
            "usage: check_imports.py PATH < SOURCE",
            file=sys.stderr,
        )
        return 2
    path = sys.argv[1]
    source = sys.stdin.read()
    if not source:
        return 0
    try:
        violations = find_violations(source)
    except SyntaxError:
        # Defer to the existing python-syntax check elsewhere
        # in pre-commit; not our job to flag syntax errors.
        return 0
    if not violations:
        return 0
    print(
        f"ERROR: {path} has stdlib `from X import` "
        f"violations:",
        file=sys.stderr,
    )
    for _, msg in violations:
        print(f"  {path}:{msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
