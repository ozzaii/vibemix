#!/usr/bin/env bash
# launch_replay.sh — deterministic, race-free, agent-owned launch of the engine-only
# co-host on a recorded set, for the autonomous QA loop (GATE-0 / 0b).
#
# Why this exists: there is no one-command launcher today. `cargo tauri dev` first-boot
# races the uv cold-sync against the Rust ws-unreachable latch (~43s) and surfaces a
# false "VIBEMIX-CORE STOPPED" (MAP-drive-app §3). The engine-only path
# (`uv run python -m vibemix`) is the only display-free, unattended-safe launch, and a
# warm `uv sync` removes the race. :8765 has no auto-free, so we free it first
# (Invariant #4, one socket).
#
# Usage:
#   scripts/qa/launch_replay.sh <session-dir>     # replay a recorded session dir
#   scripts/qa/launch_replay.sh                    # live capture (no replay) — bare engine
#
# It does NOT judge anything (that is qa_loop_run.py). It launches + proves the ws bus is
# reachable, then leaves the engine running and prints its PID + the capture session dir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SESSION_DIR="${1:-}"
WS_PORT="${VIBEMIX_WS_PORT:-8765}"
READY_BUDGET_S="${VIBEMIX_QA_READY_BUDGET_S:-120}"
LOG_DIR="${VIBEMIX_QA_LOG_DIR:-.planning/eval-runs/qa-launch}"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S 2>/dev/null || echo run)"
LOG="$LOG_DIR/launch-$STAMP.log"

echo "-> launch_replay: repo=$REPO_ROOT ws_port=$WS_PORT log=$LOG"

# 1. Warm uv sync (kills the cold-sync vs ws-latch race). Idempotent + fast when warm.
echo "-> uv sync (warm)"
uv sync >/dev/null 2>&1 || { echo "ERROR: uv sync failed" >&2; exit 1; }

# 2. Free the socket (no auto-free; second binder hits fatal exit-2 reason=port-in-use).
if lsof -ti "tcp:$WS_PORT" >/dev/null 2>&1; then
  echo "-> freeing :$WS_PORT (held)"
  lsof -ti "tcp:$WS_PORT" | xargs kill 2>/dev/null || true
  sleep 1
fi

# 3. Build the env. Engine-only headless, voice off (QA judges text, not audio out).
ENV_ARGS=(VIBEMIX_TTS_ENGINE=off VIBEMIX_DROP_DEBUG=1)
if [ -n "$SESSION_DIR" ]; then
  [ -f "$SESSION_DIR/input.wav" ] || { echo "ERROR: no input.wav under $SESSION_DIR" >&2; exit 1; }
  ENV_ARGS+=("VIBEMIX_REPLAY_SESSION=$SESSION_DIR")
  echo "-> replay session: $SESSION_DIR"
else
  echo "-> live capture (no replay session given)"
fi

# 4. Launch engine-only in the background.
echo "-> launching: uv run python -m vibemix"
env "${ENV_ARGS[@]}" uv run python -m vibemix > "$LOG" 2>&1 &
APP_PID=$!
echo "-> engine pid=$APP_PID"

# 5. Poll the ws bus until reachable (generous budget; covers a slow first boot).
echo "-> waiting for ws://127.0.0.1:$WS_PORT (budget ${READY_BUDGET_S}s)"
deadline=$((SECONDS + READY_BUDGET_S))
ready=0
while [ $SECONDS -lt $deadline ]; do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "ERROR: engine exited during boot (see $LOG)" >&2
    tail -20 "$LOG" >&2 || true
    exit 1
  fi
  if lsof -nP -iTCP:"$WS_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "ERROR: ws bus not reachable within ${READY_BUDGET_S}s (see $LOG)" >&2
  kill "$APP_PID" 2>/dev/null || true
  exit 1
fi

echo "READY ws=127.0.0.1:$WS_PORT pid=$APP_PID log=$LOG"
# The session capture dir is the newest under the recordings root; the orchestrator reads it.
echo "PID=$APP_PID"
