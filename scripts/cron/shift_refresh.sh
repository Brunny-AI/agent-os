#!/usr/bin/env bash
# shift_refresh.sh -- Agent-side trigger for shift refresh
#
# Called by the agent when it detects the shift boundary.
# Writes a flag file atomically (mktemp + mv) so the sidecar
# watcher never reads a partial file.
#
# Usage: bash scripts/cron/shift_refresh.sh <agent> <reason>
#
# The agent should call this AFTER:
#   1. Running session retrospective
#   2. Writing session-handoff.md (with sentinel)
#   3. Committing all work
#   4. Posting refresh notification to bus
#
# The sidecar watcher in agent_loop.sh will detect the flag
# and terminate the Claude session.

set -euo pipefail

readonly AGENT="${1:?Usage: shift_refresh.sh <agent> <reason>}"
readonly REASON="${2:-shift boundary reached}"
readonly WORKDIR="${AGENT_OS_ROOT:-$(pwd)}"

# Validate agent name to prevent path traversal
if [[ ! "${AGENT}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "ERROR: Invalid agent name '${AGENT}'" >&2
  echo "Agent names must match [a-zA-Z0-9_-]+" >&2
  exit 1
fi

readonly FLAG="${WORKDIR}/system/shift-refresh-${AGENT}"
readonly HANDOFF="${WORKDIR}/workspaces/${AGENT}/logs/progress/session-handoff.md"
readonly SENTINEL="--- HANDOFF COMPLETE ---"
readonly SHIFT_STATE="${WORKDIR}/system/shift-state-${AGENT}.json"

# Verify handoff file exists and has sentinel
if [[ ! -f "${HANDOFF}" ]]; then
  echo "ERROR: Handoff file not found: ${HANDOFF}" >&2
  echo "Write session-handoff.md before requesting refresh." >&2
  exit 1
fi

if ! grep -q -- "${SENTINEL}" "${HANDOFF}" 2>/dev/null; then
  echo "ERROR: Handoff file missing sentinel: ${SENTINEL}" >&2
  echo "Add '--- HANDOFF COMPLETE ---' to session-handoff.md" >&2
  exit 1
fi

# Update shift state (tracks shift count and timing)
shift_num=1
if [[ -f "${SHIFT_STATE}" ]]; then
  shift_num=$(python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        state = json.load(f)
    print(state.get('shift_count', 0) + 1)
except Exception:
    print(1)
" "${SHIFT_STATE}" || echo 1)
fi

# Atomic write for shift state (tmp + mv)
python3 -c "
import json, sys, os, tempfile
from datetime import datetime, timezone
state = {
    'agent': sys.argv[1],
    'shift_count': int(sys.argv[2]),
    'last_refresh': datetime.now(timezone.utc).isoformat(),
    'reason': sys.argv[3],
    'handoff_path': sys.argv[4]
}
state_path = sys.argv[5]
parent = os.path.dirname(state_path)
if parent:
    os.makedirs(parent, exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=parent, suffix='.tmp')
with os.fdopen(fd, 'w') as f:
    json.dump(state, f, indent=2)
os.replace(tmp, state_path)
" "${AGENT}" "${shift_num}" "${REASON}" "${HANDOFF}" "${SHIFT_STATE}"

# Atomic flag write
readonly FLAG_DIR=$(dirname "${FLAG}")
readonly FLAG_TMP=$(mktemp "${FLAG_DIR}/shift-refresh-XXXXXX.tmp")
echo "${REASON}" > "${FLAG_TMP}"
mv "${FLAG_TMP}" "${FLAG}"

echo "Shift refresh flag written for ${AGENT} (shift #${shift_num})"
echo "Reason: ${REASON}"
echo "The sidecar watcher will terminate Claude shortly."
echo "DO NOT write any more files after this point."
