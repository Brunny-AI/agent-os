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
