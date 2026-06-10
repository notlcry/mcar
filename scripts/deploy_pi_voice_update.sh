#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PI_HOST="${PI_HOST:-root@192.168.2.201}"
PI_DIR="${PI_DIR:-/root/mcar}"
PI_PYTHON="${PI_PYTHON:-/root/mcar/.venv/bin/python}"
PI_SERVICE="${PI_SERVICE:-mcar}"
BASE_URL="${BASE_URL:-http://192.168.2.201:8080}"
ROUNDS="${ROUNDS:-2}"
DRY_RUN=0

FILES=(
  "modules/robot_service/api.py"
  "modules/robot_service/adapters.py"
  "modules/robot_service/command_parser.py"
  "modules/robot_service/service.py"
  "modules/robot_service/voice_session.py"
  "modules/voice/asr.py"
  "modules/voice/capabilities.json"
  "modules/voice/driver.py"
  "modules/voice/module.py"
  "modules/voice/wake_word.py"
  "modules/tests/test_robot_service_api.py"
  "modules/tests/test_robot_service_command_parser.py"
  "modules/tests/test_robot_service_voice_session.py"
  "modules/tests/test_voice_e2e_probe_script.py"
  "modules/tests/test_aliyun_asr_hotwords_script.py"
  "modules/tests/test_voice_module.py"
  "scripts/create_aliyun_asr_hotwords.py"
  "scripts/voice_e2e_probe.py"
)

usage() {
  cat <<EOF
Usage: $0 [--dry-run]

Environment:
  PI_HOST=$PI_HOST
  PI_DIR=$PI_DIR
  PI_PYTHON=$PI_PYTHON
  PI_SERVICE=$PI_SERVICE
  BASE_URL=$BASE_URL
  ROUNDS=$ROUNDS
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

run() {
  echo "+ $*"
  if [ "$DRY_RUN" -eq 0 ]; then
    "$@"
  fi
}

remote() {
  run ssh "$PI_HOST" "$@"
}

require_files() {
  local missing=0
  for path in "${FILES[@]}"; do
    if [ ! -e "$ROOT_DIR/$path" ]; then
      echo "Missing required file: $path" >&2
      missing=1
    fi
  done
  if [ "$missing" -ne 0 ]; then
    exit 1
  fi
}

sync_files() {
  remote "mkdir -p '$PI_DIR/modules/robot_service' '$PI_DIR/modules/voice' '$PI_DIR/modules/tests' '$PI_DIR/scripts'"
  for path in "${FILES[@]}"; do
    run scp "$ROOT_DIR/$path" "$PI_HOST:$PI_DIR/$path"
  done
}

verify_remote() {
  remote "cd '$PI_DIR' && PYTHONPYCACHEPREFIX=/tmp/mcar_pycache '$PI_PYTHON' -m py_compile modules/robot_service/api.py modules/robot_service/command_parser.py modules/robot_service/service.py modules/robot_service/voice_session.py modules/voice/driver.py scripts/create_aliyun_asr_hotwords.py scripts/voice_e2e_probe.py"
  remote "cd '$PI_DIR/modules' && '$PI_PYTHON' -m pytest tests/test_robot_service_voice_session.py tests/test_robot_service_api.py::test_api_voice_run_once_triggers_voice_session tests/test_voice_e2e_probe_script.py tests/test_aliyun_asr_hotwords_script.py tests/test_voice_module.py::TestVoiceDriverASR::test_asr_payload_merges_provider_and_capture_metadata tests/test_voice_module.py::TestVoiceDriverASR::test_aliyun_funasr_uses_phrase_id_for_hotwords tests/test_voice_module.py::TestVoiceDriverASR::test_aliyun_funasr_streaming_session_passes_phrase_id_and_records_partials -q"
}

restart_service() {
  remote "systemctl restart '$PI_SERVICE'"
  remote "systemctl is-active '$PI_SERVICE'"
  wait_for_api
}

wait_for_api() {
  local attempt
  for attempt in $(seq 1 20); do
    if run curl -sS --max-time 5 "$BASE_URL/api/status"; then
      echo
      return 0
    fi
    echo "Waiting for API readiness ($attempt/20)..." >&2
    sleep 1
  done
  echo "API did not become ready: $BASE_URL/api/status" >&2
  return 1
}

run_e2e_probe() {
  run python3 "$ROOT_DIR/scripts/voice_e2e_probe.py" --base-url "$BASE_URL" --rounds "$ROUNDS"
}

require_files
sync_files
verify_remote
restart_service
run_e2e_probe
