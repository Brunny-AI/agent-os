#!/usr/bin/env bash
# Agent OS — 5-minute fresh-clone demo runner.
#
# Demonstrates all 7 MVP components end-to-end on a fresh
# install. Times each step. Designed to be recorded with
# asciinema for the README:
#
#     asciinema rec demo.cast --command 'bash examples/quickstart/run-demo.sh'
#
# Run from the repo root after `python3 setup.py init`.

set -euo pipefail

readonly DEMO_AGENT="coordinator"
readonly DEMO_PEER="builder-1"
readonly DEMO_TASK="DEMO-T1"

# Colors only when the terminal supports them. asciinema does.
if [ -t 1 ]; then
  readonly C_HEAD=$'\033[1;34m'
  readonly C_OK=$'\033[1;32m'
  readonly C_DIM=$'\033[2m'
  readonly C_OFF=$'\033[0m'
else
  readonly C_HEAD=""
  readonly C_OK=""
  readonly C_DIM=""
  readonly C_OFF=""
fi

step() {
  local n="$1"; shift
  local title="$1"; shift
  echo
  echo "${C_HEAD}[step ${n}] ${title}${C_OFF}"
}

run() {
  echo "${C_DIM}\$ $*${C_OFF}"
  "$@"
}

readonly START_TS=$(date +%s)

# Step 0 — fresh-state precondition check.
#
# If a previous `setup.py init` ran in this clone (or system/
# was copied in from another repo), partial state can survive
# in `system/` or `workspaces/`. Subsequent demo runs hit
# cryptic 'Missing bus channel' errors that look like product
# bugs but are stale-state artifacts.
#
# Detect partial state, print the actionable recovery, and
# exit. A truly-fresh clone OR a fully-initialized state both
# proceed cleanly.
echo
echo "${C_HEAD}[step 0] Check for fresh state${C_OFF}"

system_exists=0
workspaces_exists=0
[ -d system ] && system_exists=1
[ -d workspaces ] && workspaces_exists=1

if [ "${system_exists}" -eq 1 ] || [ "${workspaces_exists}" -eq 1 ]; then
  # Some state exists. Verify it's the FULL initialized shape
  # (standup + urgent channels present, ${DEMO_AGENT} workspace
  # present). If anything is missing, treat as partial.
  fully_initialized=1
  [ ! -d "system/bus/channels/standup" ] && fully_initialized=0
  [ ! -d "system/bus/channels/urgent" ] && fully_initialized=0
  [ ! -d "workspaces/${DEMO_AGENT}" ] && fully_initialized=0

  if [ "${fully_initialized}" -eq 0 ]; then
    echo "${C_OFF}" >&2
    echo "ERROR: partial state detected." >&2
    echo "  system/ exists: ${system_exists}" >&2
    echo "  workspaces/ exists: ${workspaces_exists}" >&2
    echo "  fully-initialized shape: NO" >&2
    echo "" >&2
    echo "This usually means setup.py init ran previously" >&2
    echo "but didn't complete, OR system/ was copied in from" >&2
    echo "another repo. Recover with:" >&2
    echo "" >&2
    echo "    rm -rf system workspaces" >&2
    echo "    python3 setup.py init" >&2
    echo "    bash examples/quickstart/run-demo.sh" >&2
    echo "" >&2
    exit 1
  fi
  echo "${C_OK}>> Fully-initialized state detected. Proceeding.${C_OFF}"
else
  echo "${C_OK}>> Fresh clone detected. Proceeding.${C_OFF}"
fi

step 1 "Run the test suite from a clean clone (no setup needed)"
run python3 -m unittest discover tests/ 2>&1 | tail -3
echo "${C_OK}>> Tests prove the framework before you trust it.${C_OFF}"

step 2 "Validate the install"
run python3 setup.py validate 2>&1 | tail -3

step 3 "Register a poll cron in the registry"
run python3 scripts/cron/manager.py register \
  "${DEMO_AGENT}" poll DEMO-JOB | tail -1

step 4 "Claim a task + produce a real artifact"
run python3 scripts/task/engine.py --agent "${DEMO_AGENT}" \
  --claim "${DEMO_TASK}" \
  --claim-desc "first artifact" \
  --claim-first-step "write hello" 2>&1 | tail -2
echo "print(\"hello from agent-os\")" \
  > "workspaces/${DEMO_AGENT}/hello.py"
run python3 scripts/task/engine.py --agent "${DEMO_AGENT}" \
  --artifact "${DEMO_TASK}" \
  "workspaces/${DEMO_AGENT}/hello.py" | tail -1

step 5 "Verify the v4.6 active-task gate accepts the work"
gate="$(python3 scripts/task/engine.py \
  --agent "${DEMO_AGENT}" --json-status \
  | python3 scripts/cron/poll_gates.py \
  --max-age-min 15 --blocked-grace-min 15 2>/dev/null)"
echo "  gate => ${gate}"
[ "${gate}" = "OK" ] && echo "${C_OK}>> Heartbeat would fire (gate OK).${C_OFF}"

step 6 "Send a bus message + read it as another agent"
run python3 scripts/bus/send.py \
  --channel standup --from "${DEMO_AGENT}" \
  --bus system/bus \
  --body "demo: hello world produced" | tail -1
run python3 scripts/bus/read.py \
  --agent "${DEMO_PEER}" \
  --bus system/bus \
  --offsets "workspaces/${DEMO_PEER}/memory/bus-offsets.json" \
  --peek 2>&1 | tail -5

step 7 "Output clock — see the team's status at a glance"
run python3 scripts/monitor/output_clock.py \
  --all --minutes 30 2>&1 | head -10

step 8 "Cron status — heartbeats across the team"
run python3 scripts/cron/manager.py status 2>&1 | head -8

readonly END_TS=$(date +%s)
readonly ELAPSED=$((END_TS - START_TS))

echo
echo "${C_OK}=========================================${C_OFF}"
echo "${C_OK}Demo complete in ${ELAPSED} seconds.${C_OFF}"
echo "${C_OK}All 7 MVP components ran end-to-end.${C_OFF}"
echo "${C_OK}=========================================${C_OFF}"
