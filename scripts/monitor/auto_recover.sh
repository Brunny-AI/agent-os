#!/usr/bin/env bash
# auto_recover.sh -- Restart dead agent sessions
#
# Detects expired poll heartbeats and starts new Claude
# Code sessions in detached screen or tmux windows. The
# new session runs the agent's startup prompt.
#
# Usage:
#   bash scripts/monitor/auto_recover.sh [options]
#
# Options:
#   --dry-run   Show what would restart without doing it
#   --notify    macOS notification on restart
#   --ntfy T    Push notification via ntfy.sh
#
# Requirements:
#   - screen or tmux
#   - claude CLI in PATH
#
# Called by watchdog.sh or directly via launchd/cron.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${AGENT_OS_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

readonly CRON_REGISTRY="${REPO_ROOT}/system/cron-registry.json"
readonly BUS_SCRIPTS="${REPO_ROOT}/scripts/bus"
DRY_RUN=false
NOTIFY=false
NTFY_TOPIC="${NTFY_TOPIC:-}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --notify) NOTIFY=true; shift ;;
    --ntfy) NTFY_TOPIC="$2"; shift 2 ;;
    *) shift ;;
  esac
done

send_ntfy() {
  local message="$1"
  if [ -n "${NTFY_TOPIC}" ]; then
    curl -s \
      -H "Title: Agent OS Recovery" \
      -H "Priority: high" \
      -H "Tags: robot,recycle" \
      -d "${message}" \
      "${NTFY_SERVER}/${NTFY_TOPIC}" >/dev/null 2>&1 || true
  fi
}

# Detect session manager (prefer screen, fall back to tmux)
detect_session_mgr() {
  if command -v screen >/dev/null 2>&1; then
    echo "screen"
  elif command -v tmux >/dev/null 2>&1; then
    echo "tmux"
  else
    echo ""
  fi
}

SESSION_MGR=$(detect_session_mgr)
if [ -z "${SESSION_MGR}" ] && ! ${DRY_RUN}; then
  echo "ERROR: Neither screen nor tmux found." \
       "Install one to enable auto-recovery." >&2
  exit 2
fi

if [ ! -f "${CRON_REGISTRY}" ]; then
  echo "Error: cron-registry.json not found" >&2
  exit 2
fi

# Find expired poll agents
expired_agents=$(python3 - "${CRON_REGISTRY}" 2>&1 <<'PYEOF'
import json, sys, re
from datetime import datetime, timezone, timedelta

with open(sys.argv[1]) as f:
    data = json.load(f)

now = datetime.now(timezone.utc)
valid = re.compile(r"^[a-zA-Z0-9_-]+$")

for j in data.get("jobs", []):
    if j.get("type") != "poll":
        continue
    if j.get("checked_out"):
        continue
    ldap = j.get("ldap", "")
    if not valid.match(ldap):
        continue
    timeout = j.get("heartbeat_timeout_min", 15)
    last_hb = j.get("last_heartbeat")
    if last_hb:
        hb_time = datetime.fromisoformat(
            last_hb.replace("Z", "+00:00"))
        age = now - hb_time
        if age >= timedelta(minutes=timeout):
            print(ldap)
    else:
        print(ldap)
PYEOF
)

if [ -z "${expired_agents}" ]; then
  echo "AUTO-RECOVER: All agents healthy."
  exit 0
fi

session_exists() {
  local name="$1"
  if [ "${SESSION_MGR}" = "screen" ]; then
    screen -list 2>/dev/null | grep -q "${name}"
  elif [ "${SESSION_MGR}" = "tmux" ]; then
    tmux has-session -t "${name}" 2>/dev/null
  fi
}

start_session() {
  local name="$1"
  local cmd="$2"
  if [ "${SESSION_MGR}" = "screen" ]; then
    screen -dmS "${name}" bash -c "${cmd}"
  elif [ "${SESSION_MGR}" = "tmux" ]; then
    tmux new-session -d -s "${name}" "${cmd}"
  fi
}

while IFS= read -r ldap; do
  session_name="${ldap}-agent"

  # Skip if session already exists (may be starting)
  if session_exists "${session_name}"; then
    echo "AUTO-RECOVER: Session '${session_name}'" \
         "already exists, skipping"
    continue
  fi

  # Build startup prompt
  startup_prompt="You are ${ldap}. Auto-recovered session. Working directory: ${REPO_ROOT}. Read workspaces/${ldap}/CLAUDE.md, then execute your Session Startup checklist. Note: this session was auto-started by the watchdog. Check the bus for missed messages."

  if ${DRY_RUN}; then
    echo "AUTO-RECOVER [dry-run]: Would restart ${ldap} in ${SESSION_MGR} '${session_name}'"
  else
    echo "AUTO-RECOVER: Restarting ${ldap}..."

    start_session "${session_name}" \
      "cd '${REPO_ROOT}' && claude --dangerously-skip-permissions '${startup_prompt}' 2>&1 | tee /tmp/agent-os-${ldap}-recovery.log; echo 'Session ended. Press enter.'; read"

    echo "AUTO-RECOVER: ${ldap} restarted in ${SESSION_MGR} '${session_name}'"
    echo "  Attach: ${SESSION_MGR} -r ${session_name}"

    # Bus notification (best-effort)
    python3 "${BUS_SCRIPTS}/send.py" \
      --channel urgent --from watchdog --to all \
      --body "AUTO-RECOVER: ${ldap} restarted in ${SESSION_MGR} '${session_name}'." \
      --bus "${REPO_ROOT}/system/bus" 2>&1 || true

    if ${NOTIFY}; then
      osascript -e "display notification" \
        "\"${ldap} auto-restarted\"" \
        "with title \"Agent OS\"" \
        "sound name \"Glass\"" 2>/dev/null || true
    fi
    send_ntfy "${ldap} auto-restarted in" \
      "${SESSION_MGR} ${session_name}"
  fi
done <<< "${expired_agents}"
