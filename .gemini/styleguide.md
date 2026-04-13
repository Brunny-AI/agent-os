# Agent OS Style Guide

This style guide governs all code in the agent-os repository. Gemini Code Assist should enforce these rules during pull request reviews. Contributors (human and AI) must follow these rules when writing code.

Based on [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) and [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

---

## Python

### Formatting
- **4 spaces** per indentation level. Never tabs.
- **Maximum 80 characters** per line.
- Use implicit line joining (parentheses) instead of backslash continuation.
- Sort imports lexicographically within groups: stdlib, third-party, local.
- Place imports at the top of the file, after module docstrings, before globals.

### Imports
- Use `import` for packages and modules only, not individual classes or functions.
- Never use relative imports. Always use full package names.
- No wildcard imports (`from x import *`).

### Naming
- `lower_with_under` for modules, packages, functions, methods, variables.
- `CapWords` for class names.
- `CAPS_WITH_UNDER` for module-level constants.
- Prepend single `_` for internal/protected items. Avoid double `__` prefix.

### Type Annotations
- Annotate all public API functions (parameters and return types).
- Use explicit `X | None` instead of `Optional[X]`.
- Specify type parameters for generic types (no bare `list` or `dict` in annotations).

### Docstrings
- Use triple-double-quote format (`"""`).
- Start with a one-line summary (imperative mood, e.g., "Fetch rows from the table.").
- Include `Args:`, `Returns:` (or `Yields:`), and `Raises:` sections for non-trivial functions.
- Module-level docstrings are required for all modules.

### Exceptions
- Use built-in exception classes (`ValueError`, `TypeError`, `RuntimeError`).
- Never use bare `except:` or catch generic `Exception` unless re-raising.
- Use `finally` for cleanup code.

### Other
- No mutable default arguments (use `None` and assign inside the function).
- Prefer list/dict/set comprehensions over `map()`/`filter()` for simple cases.
- Use f-strings for string formatting, not `%` or `.format()`.

---

## Shell (Bash)

### Formatting
- **2 spaces** per indentation level. Never tabs (except in `<<-` here-documents).
- **Maximum 80 characters** per line.
- Place `; then` and `; do` on the same line as `if`/`for`/`while`.
- Braces on the same line as the function name.

### Language
- Bash is the only permitted shell scripting language for executables.
- Scripts exceeding 100 lines should be considered for rewrite in Python.
- Use `#!/usr/bin/env bash` as the shebang.

### Naming
- `lowercase_with_underscores` for functions and variables.
- `UPPERCASE_WITH_UNDERSCORES` for constants and environment variables, declared at file top with `readonly`.
- Declare local variables with `local` to prevent global namespace pollution.

### Quoting
- Quote all variables and command substitutions: use `"${var}"` over `"$var"`.
- Always use `"$@"` when passing arguments, never `$*`.
- Quote strings containing spaces or shell metacharacters.

### Error Handling
- All error messages must go to STDERR (`>&2`).
- Always check return values using `$?` or conditional `if` statements.
- Exit with non-zero codes when errors occur.
- Use `PIPESTATUS` array to check all pipe segment exit codes when needed.

### Functions
- All functions require a header comment describing: purpose, globals used, arguments, outputs, and return values.
- No space between function name and parenthesis.

---

## General Rules (All Languages)

### Security
- Never hardcode secrets, API keys, or credentials. Use environment variables.
- Validate all external input at system boundaries.
- No command injection vulnerabilities (quote all shell variables, use parameterized queries).

### Code Review Focus Areas
When reviewing pull requests, prioritize in this order:
1. **Correctness** — Does the code do what it claims?
2. **Security** — Are there injection, credential, or access control issues?
3. **Maintainability** — Is it readable and well-structured?
4. **Efficiency** — Are there unnecessary operations or O(n^2) patterns?
5. **Testing** — Are edge cases covered?

### Commit Messages
- Format: `[agent] verb: description`
- Verbs: add, fix, update, remove, refactor
- Include a `Now possible:` line describing what this change enables.

### PR Requirements
- Every PR must be under 1000 lines changed.
- Every PR must include a summary and test plan.
- Branch naming: `{agent}/{description}` (e.g., `scout/port-event-bus`).
