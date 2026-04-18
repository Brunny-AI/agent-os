"""check_imports.py: stdlib `from X import` lint.

Pins the contract that the same `from datetime import datetime`
class drift caught manually in PR #24/#29/#30 R1 fails LOCAL
pre-commit instead of needing a Step 6 round.
"""

from __future__ import annotations

import importlib.util
import os
import unittest


_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_HOOK = os.path.join(
    _REPO, "scripts", "hooks", "check_imports.py"
)


def _load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "_check_imports", _HOOK
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CheckImportsTest(unittest.TestCase):
    """Stdlib `from X import` flagged; common exemptions pass."""

    def setUp(self) -> None:
        self.mod = _load_module()

    def test_from_datetime_flagged(self) -> None:
        src = (
            "from datetime import datetime, timezone\n"
            "x = datetime.now()\n"
        )
        violations = self.mod.find_violations(src)
        self.assertEqual(len(violations), 1)
        lineno, msg = violations[0]
        self.assertEqual(lineno, 1)
        self.assertIn("datetime", msg)
        self.assertIn("rule 19", msg)

    def test_top_level_import_passes(self) -> None:
        src = (
            "import datetime\n"
            "x = datetime.datetime.now(datetime.timezone.utc)\n"
        )
        self.assertEqual(self.mod.find_violations(src), [])

    def test_typing_exempt(self) -> None:
        # Google itself uses `from typing import Any, Callable`
        src = "from typing import Any, Callable\n"
        self.assertEqual(self.mod.find_violations(src), [])

    def test_future_exempt(self) -> None:
        src = "from __future__ import annotations\n"
        self.assertEqual(self.mod.find_violations(src), [])

    def test_relative_import_skipped(self) -> None:
        # `from . import x` is relative; not our concern.
        src = "from . import sibling\n"
        self.assertEqual(self.mod.find_violations(src), [])

    def test_third_party_unflagged_for_now(self) -> None:
        # We deliberately scope to stdlib — third-party
        # `from yaml import safe_load` is common idiom and
        # outside this rule's drift target.
        src = "from yaml import safe_load\n"
        self.assertEqual(self.mod.find_violations(src), [])

    def test_dotted_module_root_resolved(self) -> None:
        # `from os.path import join` should flag (root is os).
        src = "from os.path import join\n"
        violations = self.mod.find_violations(src)
        self.assertEqual(len(violations), 1)
        self.assertIn("os.path", violations[0][1])

    def test_multiple_violations_all_reported(self) -> None:
        src = (
            "from datetime import datetime\n"
            "from os import path\n"
            "from json import loads\n"
        )
        violations = self.mod.find_violations(src)
        self.assertEqual(len(violations), 3)
        # In source order
        self.assertEqual(
            [v[0] for v in violations], [1, 2, 3]
        )

    def test_syntax_error_swallowed(self) -> None:
        # The python-syntax check elsewhere in pre-commit owns
        # syntax-error reporting; we must not double-error.
        # (find_violations RAISES, but the CLI swallows.)
        with self.assertRaises(SyntaxError):
            self.mod.find_violations("def broken(\n")


if __name__ == "__main__":
    unittest.main()
