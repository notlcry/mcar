#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CORE_DIR="$ROOT_DIR/core"
ENV_FILE="$ROOT_DIR/.ai_pet_env"
PID_FILE="$ROOT_DIR/mcar.pid"
LOG_DIR="$ROOT_DIR/logs"
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
LOG_FILE="$LOG_DIR/mcar-$STAMP.log"

VENV_DIR="${MCAR_VENV_DIR:-$ROOT_DIR/.venv}"
if [[ ! -x "$VENV_DIR/bin/python" ]] && [[ -x "$ROOT_DIR/.venv-gate/bin/python" ]]; then
  VENV_DIR="$ROOT_DIR/.venv-gate"
fi

if [[ ! -f "$CORE_DIR/dist/index.js" ]]; then
  echo "[ERROR] core/dist/index.js not found. Run: cd $CORE_DIR && npm run build" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

PORT="${WEB_PORT:-8080}"
STATUS_URL="http://127.0.0.1:${PORT}/api/status"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "[INFO] mcar already running (pid=$old_pid)"
    echo "[INFO] status check: $STATUS_URL"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

mkdir -p "$LOG_DIR"

start_prefix=()
if command -v ionice >/dev/null 2>&1; then
  start_prefix=(ionice -c2 -n7 nice -n 10)
elif command -v nice >/dev/null 2>&1; then
  start_prefix=(nice -n 10)
fi

(
  cd "$CORE_DIR"
  PATH="$VENV_DIR/bin:$PATH" nohup "${start_prefix[@]}" node dist/index.js >>"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
)

pid="$(cat "$PID_FILE")"
ready=0

for _ in $(seq 1 30); do
  if curl --noproxy "*" -sS -m 2 "$STATUS_URL" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" -ne 1 ]]; then
  echo "[ERROR] service failed to become ready: $STATUS_URL" >&2
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE"
  echo "[ERROR] last log lines:"
  tail -n 60 "$LOG_FILE" || true
  exit 1
fi

echo "[OK] mcar started (pid=$pid)"
echo "[OK] status: $STATUS_URL"
echo "[OK] pid file: $PID_FILE"
echo "[OK] log file: $LOG_FILE"
