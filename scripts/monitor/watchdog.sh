#!/usr/bin/env bash
# watchdog.sh -- External session watchdog
#
# Runs outside Claude Code (via launchd or system cron).
# Checks agent heartbeats in cron-registry.json. If any
# poll heartbeat is expired, sends an alert to the bus
# urgent channel and optionally to macOS and mobile.
#
# Usage:
#   bash scripts/monitor/watchdog.sh [options]
#
# Options:
#   --notify        Show macOS notification
#   --ntfy TOPIC    Push notification via ntfy.sh
#                   (free, no signup required)
#
# Environment variables (alternative to flags):
#   AGENT_OS_ROOT   Root directory (default: auto-detect)
#   NTFY_TOPIC      ntfy.sh topic name
#   NTFY_SERVER     ntfy server URL (default: ntfy.sh)
#
# Exit codes:
#   0  All agents healthy
#   1  One or more agents expired (alert sent)
#   2  No agents registered (alert sent)

set -e

# Auto-detect repo root from script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${AGENT_OS_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

readonly CRON_REGISTRY="${REPO_ROOT}/system/cron-registry.json"
readonly BUS_SCRIPTS="${REPO_ROOT}/scripts/bus"
NOTIFY=false
NTFY_TOPIC="${NTFY_TOPIC:-}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.sh}"

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    --notify) NOTIFY=true; shift ;;
    --ntfy) NTFY_TOPIC="$2"; shift 2 ;;
    *) shift ;;
  esac
done

send_ntfy() {
  local message="$1"
  local priority="${2:-urgent}"
  if [ -n "${NTFY_TOPIC}" ]; then
    curl -s \
      -H "Title: Agent OS Watchdog" \
      -H "Priority: ${priority}" \
      -H "Tags: warning,robot" \
      -d "${message}" \
      "${NTFY_SERVER}/${NTFY_TOPIC}" >/dev/null 2>&1 || true
  fi
}

if [ ! -f "${CRON_REGISTRY}" ]; then
  echo "Error: cron-registry.json not found" \
       "at ${CRON_REGISTRY}" >&2
  exit 2
fi

# Check poll heartbeats (ignore meeting jobs)
expired=$(python3 - "${CRON_REGISTRY}" 2>&1 <<'PYEOF'
import json, sys
from datetime import datetime, timezone, timedelta

with open(sys.argv[1]) as f:
    data = json.load(f)

now = datetime.now(timezone.utc)
expired = []

for j in data.get("jobs", []):
    if j.get("type") != "poll":
        continue
    if j.get("checked_out"):
        continue
    timeout = j.get("heartbeat_timeout_min", 15)
    last_hb = j.get("last_heartbeat")
    if last_hb:
        hb_time = datetime.fromisoformat(
            last_hb.replace("Z", "+00:00"))
        age = now - hb_time
        if age >= timedelta(minutes=timeout):
            age_min = int(age.total_seconds() / 60)
            expired.append(
                f'{j["ldap"]} (last heartbeat'
                f' {age_min}m ago, timeout {timeout}m)')
    else:
        expired.append(f'{j["ldap"]} (never heartbeated)')

if expired:
    for e in expired:
        print(e)
PYEOF
)

if [ -z "${expired}" ]; then
  # Check if ANY poll jobs exist
  poll_count=$(python3 - "${CRON_REGISTRY}" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
print(sum(1 for j in data.get("jobs", [])
          if j.get("type") == "poll"))
PYEOF
)
  if [ "${poll_count}" = "0" ]; then
    msg="WATCHDOG: No agent poll jobs registered. All agents may be down."
    echo "${msg}"
    python3 "${BUS_SCRIPTS}/send.py" \
      --channel urgent --from watchdog --to all \
      --body "${msg}" \
      --bus "${REPO_ROOT}/system/bus" 2>&1
    if ${NOTIFY}; then
      osascript -e 'display notification' \
        '"No agent sessions detected"' \
        'with title "Agent OS Watchdog"' \
        'sound name "Sosumi"' 2>/dev/null || true
    fi
    send_ntfy "All agents may be down." \
              "No poll jobs registered."
    exit 2
  fi
  exit 0
fi

# One or more agents expired
echo "WATCHDOG: Expired agents:"
echo "${expired}"

# Attempt auto-recovery
RECOVER_SCRIPT="${SCRIPT_DIR}/auto_recover.sh"
if [ -f "${RECOVER_SCRIPT}" ]; then
  echo "WATCHDOG: Attempting auto-recovery..."
  RECOVER_ARGS=""
  ${NOTIFY} && RECOVER_ARGS="${RECOVER_ARGS} --notify"
  [ -n "${NTFY_TOPIC}" ] && \
    RECOVER_ARGS="${RECOVER_ARGS} --ntfy ${NTFY_TOPIC}"
  # shellcheck disable=SC2086
  bash "${RECOVER_SCRIPT}" ${RECOVER_ARGS} 2>&1
else
  # Fallback: alert only
  alert_body="WATCHDOG: Expired agent sessions. $(echo "${expired}" | tr '\n' '; '). Restart needed."
  python3 "${BUS_SCRIPTS}/send.py" \
    --channel urgent --from watchdog --to all \
    --body "${alert_body}" \
    --bus "${REPO_ROOT}/system/bus" 2>&1

  if ${NOTIFY}; then
    osascript -e "display notification" \
      "\"$(echo "${expired}" | head -1)\"" \
      "with title \"Agent OS Watchdog\"" \
      "sound name \"Sosumi\"" 2>/dev/null || true
  fi
  send_ntfy "Agent down:" \
    "$(echo "${expired}" | tr '\n' '; ')." \
    "Restart needed."
fi

exit 1
