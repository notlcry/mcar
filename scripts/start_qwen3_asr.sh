#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${QWEN3_ASR_VENV_DIR:-$ROOT_DIR/.qwen3-asr-venv}"
LOG_DIR="${QWEN3_ASR_LOG_DIR:-$ROOT_DIR/logs}"
PID_FILE="${QWEN3_ASR_PID_FILE:-$LOG_DIR/qwen3-asr.pid}"
LOG_FILE="${QWEN3_ASR_LOG_FILE:-$LOG_DIR/qwen3-asr.log}"

_detect_host() {
  if command -v ipconfig >/dev/null 2>&1; then
    ipconfig getifaddr en0 2>/dev/null && return
    ipconfig getifaddr en1 2>/dev/null && return
  fi
  echo "127.0.0.1"
}

HOST="${QWEN3_ASR_HOST:-$(_detect_host)}"
PORT="${QWEN3_ASR_PORT:-8765}"
MODEL="${QWEN3_ASR_MODEL:-Qwen/Qwen3-ASR-0.6B}"
HF_HOME="${HF_HOME:-$ROOT_DIR/.hf-cache}"
DEVICE_MAP="${QWEN3_ASR_DEVICE_MAP:-auto}"
DTYPE="${QWEN3_ASR_DTYPE:-float32}"

usage() {
  cat <<USAGE
Usage: $0 [start|foreground|stop|restart|status|logs]

Environment overrides:
  QWEN3_ASR_HOST=$HOST
  QWEN3_ASR_PORT=$PORT
  QWEN3_ASR_MODEL=$MODEL
  HF_HOME=$HF_HOME
USAGE
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE")"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

health_ok() {
  curl -fsS --max-time 2 "http://$HOST:$PORT/health" >/dev/null 2>&1
}

ensure_venv() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    return
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required to create $VENV_DIR" >&2
    exit 1
  fi

  echo "[STEP] Create venv: $VENV_DIR"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/mcar-uv-cache}" uv venv --python 3.12 "$VENV_DIR"

  echo "[STEP] Install Qwen3-ASR server dependencies"
  UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/mcar-uv-cache}" \
    uv pip install --python "$VENV_DIR/bin/python" -e "$ROOT_DIR/modules[qwen3-asr-server]"
}

start() {
  mkdir -p "$LOG_DIR" "$HF_HOME"
  ensure_venv

  if is_running; then
    echo "[OK] Qwen3-ASR already running: pid=$(cat "$PID_FILE") url=http://$HOST:$PORT"
    return
  fi
  if health_ok; then
    echo "[OK] Qwen3-ASR already reachable: url=http://$HOST:$PORT"
    return
  fi

  echo "[STEP] Start Qwen3-ASR: http://$HOST:$PORT"
  (
    cd "$ROOT_DIR"
    export HF_HOME
    export QWEN3_ASR_MODEL="$MODEL"
    export QWEN3_ASR_DEVICE_MAP="$DEVICE_MAP"
    export QWEN3_ASR_DTYPE="$DTYPE"
    nohup "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/qwen3_asr_server.py" \
      --host "$HOST" \
      --port "$PORT" \
      >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )
  sleep 2

  if is_running; then
    echo "[OK] Qwen3-ASR started: pid=$(cat "$PID_FILE")"
    echo "[OK] health: http://$HOST:$PORT/health"
    echo "[OK] log: $LOG_FILE"
  else
    echo "[FAIL] Qwen3-ASR exited during startup. Log:" >&2
    tail -n 80 "$LOG_FILE" >&2 || true
    exit 1
  fi
}

foreground() {
  mkdir -p "$LOG_DIR" "$HF_HOME"
  ensure_venv

  echo $$ > "$PID_FILE"
  cd "$ROOT_DIR"
  export HF_HOME
  export QWEN3_ASR_MODEL="$MODEL"
  export QWEN3_ASR_DEVICE_MAP="$DEVICE_MAP"
  export QWEN3_ASR_DTYPE="$DTYPE"
  exec "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/qwen3_asr_server.py" \
    --host "$HOST" \
    --port "$PORT"
}

stop() {
  if ! is_running; then
    echo "[OK] Qwen3-ASR not running"
    rm -f "$PID_FILE"
    return
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  echo "[STEP] Stop Qwen3-ASR: pid=$pid"
  kill "$pid"
  for _ in {1..20}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$PID_FILE"
      echo "[OK] stopped"
      return
    fi
    sleep 0.2
  done

  echo "[WARN] Process did not stop after SIGTERM; sending SIGKILL"
  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
}

status() {
  if is_running; then
    echo "[OK] running: pid=$(cat "$PID_FILE") url=http://$HOST:$PORT"
    curl -sS --max-time 5 "http://$HOST:$PORT/health" || true
    echo
  elif health_ok; then
    echo "[OK] running: pid=unknown url=http://$HOST:$PORT"
    curl -sS --max-time 5 "http://$HOST:$PORT/health" || true
    echo
  else
    echo "[OK] not running"
  fi
}

case "${1:-start}" in
  start)
    start
    ;;
  foreground)
    foreground
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    start
    ;;
  status)
    status
    ;;
  logs)
    tail -n 120 -f "$LOG_FILE"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
