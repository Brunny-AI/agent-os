# Config Loader

Override-based configuration system. Core ships defaults,
users customize via overrides. No full config file needed.

## Quick Start

```bash
# Show merged config
python scripts/config/loader.py

# Get a specific value
python scripts/config/loader.py --key bus.root

# Validate configuration
python scripts/config/loader.py --validate

# JSON output
python scripts/config/loader.py --json
```

## How It Works

1. Loads `defaults/agent-os.yaml` (shipped, read-only)
2. If `config/agent-os.yaml` exists, merges it on top
3. Deep merge: dicts recurse, lists replace, scalars overwrite

## Override Example

Only include keys you want to change:

```yaml
# config/agent-os.yaml
team:
  name: "my-team"
tasks:
  lease_minutes: 30
```

Everything else keeps the defaults.

## Use in Scripts

```python
from scripts.config.loader import load_config, get_value

cfg = load_config()
ttl = get_value(cfg, "bus.default_ttl_hours")
```

## YAML Support

Works without PyYAML using a built-in minimal parser.

**Supported (minimal parser):**
- `key: value` (scalars: strings, ints, bools, null)
- Nested mappings (indent-based)
- Simple lists (`- item`, `- key: value`)
- Comments (`#`)
- Quoted strings (`"value"`, `'value'`)

**NOT supported (install PyYAML for these):**
- Flow mappings/sequences (`{}`, `[]` inline)
- Multi-line strings (`|`, `>`)
- Anchors and aliases (`&`, `*`)
- Tags (`!!`)
- Complex nesting beyond 2-space indent

Install PyYAML: `pip install pyyaml` (optional, auto-detected).
