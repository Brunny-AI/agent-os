#!/usr/bin/env bash
# agent_loop.sh -- Wrapper for autonomous shift refresh
#
# Runs Claude Code in a loop with a sidecar watcher. When
# the agent writes a shift-refresh flag file, the sidecar
# detects it and kills Claude externally. The wrapper then
# restarts with fresh context.
#
# Claude Code refuses to kill its parent process (safety
# guardrail), so the sidecar pattern is the proven
# alternative for automated restarts.
#
# Usage: bash scripts/cron/agent_loop.sh <agent> [root-dir]
#   e.g.: bash scripts/cron/agent_loop.sh builder-1
#
# Logs: workspaces/<agent>/logs/shift/agent-loop.log
#       workspaces/<agent>/logs/shift/events.jsonl
#
# Race condition mitigations:
#   1. Flag file: atomic write (tmp + mv) prevents
#      sidecar from reading partial content
#   2. Git lock: sidecar checks for .git/index.lock
#      before killing -- won't kill mid-commit
#   3. Grace period: configurable delay between flag
#      detection and kill for I/O completion
#   4. Process verification: sidecar confirms PID is
#      still claude before sending signal
#   5. Singleton lock: only one wrapper per agent
#   6. Trap handlers: clean up on wrapper death

# NOTE: Do NOT use set -e. wait on a killed process
# returns 128+signal which would trigger errexit and
# skip all post-exit logic (refresh, crash loop, cleanup).
set -uo pipefail

readonly AGENT="${1:?Usage: agent_loop.sh <agent> [root-dir]}"
WORKDIR_RAW="${2:-$(pwd)}"
WORKDIR=$(cd "${WORKDIR_RAW}" && pwd -P)

# Validate agent name (prevent path traversal)
if [[ ! "${AGENT}" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "ERROR: Invalid agent name '${AGENT}'" >&2
  echo "Agent names must match [a-zA-Z0-9_-]+" >&2
  exit 1
fi

# Paths (relative to AGENT_OS_ROOT)
readonly FLAG="${WORKDIR}/system/shift-refresh-${AGENT}"
readonly HANDOFF="${WORKDIR}/workspaces/${AGENT}/logs/progress/session-handoff.md"
readonly SENTINEL="--- HANDOFF COMPLETE ---"
readonly GIT_LOCK="${WORKDIR}/workspaces/.git/index.lock"
readonly LOCK_DIR="${WORKDIR}/system/.agent-loop-${AGENT}.lock.d"
readonly LOCK_PID="${WORKDIR}/system/.agent-loop-${AGENT}.lock.pid"

# Read config values with fallbacks
# Passes paths via sys.argv to avoid code injection
read_config() {
  local key="$1"
  local default="$2"
  python3 - "${WORKDIR}" "${key}" "${default}" <<'PYEOF'
import sys
workdir, key, default = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, f"{workdir}/scripts/config")
try:
    from loader import load_config
    cfg = load_config(workdir)
    val = cfg
    for k in key.split("."):
        val = val[k]
    print(val)
except Exception:
    print(default)
PYEOF
}

# Configurable parameters
MAX_RAPID_RESTARTS=3
RAPID_THRESHOLD=30
GRACE_PERIOD=$(read_config "autonomous.grace_period_seconds" "3")
SIDECAR_POLL=$(read_config "autonomous.sidecar_poll_seconds" "2")
SHIFT=0
rapid_count=0
CLAUDE_PID=""
WATCHER_PID=""

# --- Logging ---
LOG_DIR="${WORKDIR}/workspaces/${AGENT}/logs/shift"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/agent-loop.log"

log() {
  local level="$1"
  shift
  local msg
  msg="$(date -u +%Y-%m-%dT%H:%M:%SZ) [${level}] [shift=${SHIFT}] $*"
  echo "${msg}" | tee -a "${LOG_FILE}"
}

log_event() {
  local event="$1"
  shift
  local detail="$*"
  python3 - "${AGENT}" "${SHIFT}" "${event}" "${detail}" \
    >> "${LOG_DIR}/events.jsonl" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
obj = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "agent": sys.argv[1],
    "shift": int(sys.argv[2]),
    "event": sys.argv[3],
    "detail": sys.argv[4]
}
print(json.dumps(obj, ensure_ascii=False))
PYEOF
  log "INFO" "${event}: ${detail}"
}

cd "${WORKDIR}"

# --- Singleton Lock ---
# Prevent two wrappers for the same agent from running
# simultaneously. Uses mkdir as atomic lock (portable).
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  if [ -f "${LOCK_PID}" ] && \
     kill -0 "$(cat "${LOCK_PID}" 2>/dev/null)" 2>/dev/null
  then
    echo "[agent-loop] ERROR: Another instance for" \
         "${AGENT} is running (pid=$(cat "${LOCK_PID}"))" >&2
    exit 1
  else
    echo "[agent-loop] WARN: Removing stale lock" >&2
    rm -rf "${LOCK_DIR}" "${LOCK_PID}"
    mkdir "${LOCK_DIR}" 2>/dev/null || {
      echo "[agent-loop] ERROR: Could not acquire lock" >&2
      exit 1
    }
  fi
fi
echo $$ > "${LOCK_PID}"

# --- Trap Handlers ---
cleanup() {
  log "WARN" "Cleanup triggered (trap)"
  if [ -n "${WATCHER_PID}" ] && \
     kill -0 "${WATCHER_PID}" 2>/dev/null; then
    kill "${WATCHER_PID}" 2>/dev/null || true
    log "INFO" "Killed watcher (pid=${WATCHER_PID})"
  fi
  if [ -n "${CLAUDE_PID}" ] && \
     kill -0 "${CLAUDE_PID}" 2>/dev/null; then
    kill "${CLAUDE_PID}" 2>/dev/null || true
    log "INFO" "Killed Claude (pid=${CLAUDE_PID})"
  fi
  rm -rf "${LOCK_DIR}" "${LOCK_PID}" 2>/dev/null || true
  log_event "WRAPPER_CLEANUP" "trapped"
}
trap cleanup EXIT INT TERM HUP

log "INFO" "=== agent_loop.sh starting for ${AGENT}" \
     "(wrapper pid $$) ==="
log "INFO" "Working dir: ${WORKDIR}"
log "INFO" "Flag path: ${FLAG}"
log_event "WRAPPER_START" "pid=$$ agent=${AGENT}"

# --- Startup Prompt Resolver ---
# Reads the prompt template for session start or refresh.
# Falls back to a simple default if the file doesn't exist.
resolve_prompt() {
  local prompt_type="$1"
  local prompt_file="${WORKDIR}/defaults/prompts/${prompt_type}.md"
  if [ -f "${prompt_file}" ]; then
    # Replace {agent} placeholder with actual agent name
    sed "s/{agent}/${AGENT}/g" "${prompt_file}"
  else
    # Minimal fallback
    if [ "${prompt_type}" = "session-start" ]; then
      echo "You are ${AGENT}. Read your CLAUDE.md, set up" \
           "your poll cron, and start working."
    else
      echo "You are ${AGENT}. Read your session handoff," \
           "restore crons, and resume your task."
    fi
  fi
}

# --- Sidecar Flag Watcher ---
start_flag_watcher() {
  local claude_pid=$1
  local flag_path=$2
  local log_file=$3
  local events_file="${LOG_DIR}/events.jsonl"
  (
    while kill -0 "${claude_pid}" 2>/dev/null; do
      if [ -f "${flag_path}" ]; then
        local reason
        reason=$(cat "${flag_path}" 2>/dev/null || echo "unknown")
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
             "Flag detected. Reason: ${reason}" >> "${log_file}"

        # Wait for git lock to clear (up to 30s)
        local git_wait=0
        while [ -f "${GIT_LOCK}" ] && [ ${git_wait} -lt 30 ]; do
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "Git lock active, waiting..." \
               "(${git_wait}/30s)" >> "${log_file}"
          sleep 1
          git_wait=$((git_wait + 1))
        done
        if [ ${git_wait} -ge 30 ]; then
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "WARNING: Git lock timeout, proceeding" \
               >> "${log_file}"
        fi

        # Verify PID is still claude
        local proc_name
        proc_name=$(ps -p "${claude_pid}" -o comm= \
                    2>/dev/null || echo "dead")
        if [ "${proc_name}" != "claude" ] && \
           [ "${proc_name}" != "node" ]; then
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "WARNING: PID ${claude_pid} is" \
               "'${proc_name}' not 'claude'." \
               "Flag preserved." >> "${log_file}"
          break
        fi

        # Grace period for I/O completion
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
             "Grace period ${GRACE_PERIOD}s..." \
             >> "${log_file}"
        sleep "${GRACE_PERIOD}"

        # Kill with SIGTERM, escalate to SIGKILL
        if kill -0 "${claude_pid}" 2>/dev/null; then
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "Sending SIGTERM to Claude" \
               "(pid ${claude_pid})" >> "${log_file}"
          kill "${claude_pid}" 2>/dev/null

          local kill_wait=0
          while kill -0 "${claude_pid}" 2>/dev/null && \
                [ ${kill_wait} -lt 10 ]; do
            sleep 1
            kill_wait=$((kill_wait + 1))
          done
          if kill -0 "${claude_pid}" 2>/dev/null; then
            echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                 "[SIDECAR] SIGTERM timeout." \
                 "Sending SIGKILL." >> "${log_file}"
            kill -9 "${claude_pid}" 2>/dev/null
          fi
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "Claude terminated." >> "${log_file}"
          python3 - "${AGENT}" "${SHIFT}" \
            "pid=${claude_pid}" \
            >> "${events_file}" 2>/dev/null <<'PYEOF'
import json, sys
from datetime import datetime, timezone
print(json.dumps({
    "ts": datetime.now(timezone.utc).isoformat(),
    "agent": sys.argv[1],
    "shift": int(sys.argv[2]),
    "event": "SIDECAR_KILL",
    "detail": sys.argv[3]
}))
PYEOF
        else
          echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
               "Claude already exited." >> "${log_file}"
        fi
        break
      fi
      sleep "${SIDECAR_POLL}"
    done
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [SIDECAR]" \
         "Watcher exiting." >> "${log_file}"
  ) &
  echo $!
}

# --- Main Loop ---
while true; do
  SHIFT=$((SHIFT + 1))
  start_time=$(date +%s)

  log_event "SHIFT_START" "shift=${SHIFT}"

  # Clean stale flag from previous shift
  if [ -f "${FLAG}" ]; then
    log "WARN" "Stale flag file found, removing"
    rm -f "${FLAG}"
  fi

  # Resolve the startup prompt
  if [ "${SHIFT}" -eq 1 ]; then
    prompt=$(resolve_prompt "session-start")
    log "INFO" "Starting Claude (shift 1, session-start)"
  else
    prompt=$(resolve_prompt "session-refresh")
    log "INFO" "Starting Claude (shift ${SHIFT}," \
         "session-refresh)"
  fi

  # Run Claude Code in background
  claude --dangerously-skip-permissions \
         "${prompt}" &
  CLAUDE_PID=$!

  log_event "CLAUDE_START" \
            "pid=${CLAUDE_PID} shift=${SHIFT}"

  # Start sidecar flag watcher
  WATCHER_PID=$(start_flag_watcher \
    "${CLAUDE_PID}" "${FLAG}" "${LOG_FILE}")
  log "INFO" "Sidecar started (pid=${WATCHER_PID}," \
       "polling every ${SIDECAR_POLL}s)"
  log_event "SIDECAR_START" \
    "watcher_pid=${WATCHER_PID} claude_pid=${CLAUDE_PID}"

  # Wait for Claude to exit (naturally or via sidecar)
  wait "${CLAUDE_PID}" 2>/dev/null
  CLAUDE_EXIT=$?
  end_time=$(date +%s)
  duration=$((end_time - start_time))

  log_event "CLAUDE_EXIT" \
    "exit_code=${CLAUDE_EXIT} duration=${duration}s"

  # Clean up sidecar
  if [ -n "${WATCHER_PID}" ] && \
     kill -0 "${WATCHER_PID}" 2>/dev/null; then
    kill "${WATCHER_PID}" 2>/dev/null || true
    wait "${WATCHER_PID}" 2>/dev/null || true
    log "INFO" "Sidecar cleaned up (pid=${WATCHER_PID})"
  fi
  WATCHER_PID=""

  # --- Decide what to do ---

  # Case 1: Shift refresh requested
  if [ -f "${FLAG}" ]; then
    REASON=$(cat "${FLAG}" 2>/dev/null || echo "unknown")
    log_event "SHIFT_REFRESH" \
      "reason=${REASON} duration=${duration}s"

    if [ -f "${HANDOFF}" ] && \
       grep -q -- "${SENTINEL}" "${HANDOFF}" 2>/dev/null
    then
      log "INFO" "Handoff validated (sentinel found)"
    else
      log "WARN" "Handoff invalid or missing sentinel"
    fi

    rm -f "${FLAG}"
    rapid_count=0
    log "INFO" "Restarting with fresh context..."
    log_event "SHIFT_RESTART" \
      "next_shift=$((SHIFT + 1))"

    # Bus notification (best-effort)
    python3 "${WORKDIR}/scripts/bus/send.py" \
      --channel standup --from "${AGENT}" \
      --body "SHIFT REFRESH: ${AGENT} completed shift ${SHIFT} (${duration}s). Reason: ${REASON}. Restarting." \
      --bus "${WORKDIR}/system/bus" 2>/dev/null || true

    CLAUDE_PID=""
    continue
  fi

  CLAUDE_PID=""

  # Case 2: Rapid exit (potential crash)
  if [ "${duration}" -lt "${RAPID_THRESHOLD}" ]; then
    rapid_count=$((rapid_count + 1))
    log "WARN" "Rapid exit #${rapid_count}" \
         "(${duration}s < ${RAPID_THRESHOLD}s)"
    log_event "RAPID_EXIT" \
      "count=${rapid_count} exit_code=${CLAUDE_EXIT}"

    if [ "${rapid_count}" -ge "${MAX_RAPID_RESTARTS}" ]; then
      log "ERROR" "CRASH LOOP: ${rapid_count} rapid exits"
      log_event "CRASH_LOOP" "count=${rapid_count}"

      python3 "${WORKDIR}/scripts/bus/send.py" \
        --channel urgent --from "${AGENT}" \
        --body "CRASH LOOP: agent_loop.sh for ${AGENT} hit ${rapid_count} rapid exits. Exit code: ${CLAUDE_EXIT}. Manual intervention needed." \
        --bus "${WORKDIR}/system/bus" 2>/dev/null || true
      exit 1
    fi

    # Exponential backoff: 5s, 30s, 300s
    case ${rapid_count} in
      1) log "INFO" "Backoff: 5s"; sleep 5 ;;
      2) log "INFO" "Backoff: 30s"; sleep 30 ;;
      *) log "INFO" "Backoff: 300s"; sleep 300 ;;
    esac
    continue
  fi

  # Case 3: Normal exit (no flag)
  log "INFO" "Normal exit after ${duration}s. Stopping."
  log_event "NORMAL_EXIT" \
    "duration=${duration}s exit_code=${CLAUDE_EXIT}"
  break
done

log_event "WRAPPER_EXIT" "total_shifts=${SHIFT}"
log "INFO" "=== agent_loop.sh ended after" \
     "${SHIFT} shift(s) ==="
