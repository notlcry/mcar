#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_GATE_A="${SKIP_GATE_A:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Keep gate execution at low priority to reduce SSH/network starvation on Raspberry Pi.
# Re-exec only once to avoid recursion.
if [[ "${MCAR_GATE_CHILD:-0}" != "1" ]]; then
  if command -v ionice >/dev/null 2>&1; then
    exec env MCAR_GATE_CHILD=1 ionice -c2 -n7 nice -n 10 bash "$0" "$@"
  elif command -v nice >/dev/null 2>&1; then
    exec env MCAR_GATE_CHILD=1 nice -n 10 bash "$0" "$@"
  fi
fi

STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
OUT_DIR="$ROOT_DIR/docs/verification/run-$STAMP"
REPORT="$OUT_DIR/report.md"
BASE_URL="${BASE_URL:-http://127.0.0.1:${WEB_PORT:-8080}}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv-gate}"
IGNORE_BUTTON_HW="${IGNORE_BUTTON_HW:-1}"

mkdir -p "$OUT_DIR"

COMMAND_LOG="$OUT_DIR/commands.log"
BLOCKERS_FILE="$OUT_DIR/blocking_issues.txt"
RISKS_FILE="$OUT_DIR/hardware_risks.txt"
RETEST_FILE="$OUT_DIR/retest_suggestions.txt"

: > "$COMMAND_LOG"
: > "$BLOCKERS_FILE"
: > "$RISKS_FILE"
: > "$RETEST_FILE"

pass_count=0
fail_count=0
na_count=0
blocked_count=0
gatea_fail=0

service_pid=""
service_started=0

API_OUT=""
API_HTTP=""
API_LOG=""
API_CODE=""

rel_path() {
  local path="$1"
  echo "${path#$ROOT_DIR/}"
}

log_cmd() {
  local gate="$1"
  local item="$2"
  local cmd="$3"
  printf '[%s] [%s|%s] %s\n' "$(date +%Y-%m-%d_%H-%M-%S)" "$gate" "$item" "$cmd" >> "$COMMAND_LOG"
}

add_retest() {
  local suggestion="$1"
  if ! grep -Fqx "$suggestion" "$RETEST_FILE" 2>/dev/null; then
    echo "$suggestion" >> "$RETEST_FILE"
  fi
}

record() {
  local status="$1"
  local gate="$2"
  local item="$3"
  local detail="$4"

  case "$status" in
    PASS)
      pass_count=$((pass_count + 1))
      ;;
    FAIL)
      fail_count=$((fail_count + 1))
      printf -- "- %s | %s | %s\n" "$gate" "$item" "$detail" >> "$BLOCKERS_FILE"
      ;;
    NA)
      na_count=$((na_count + 1))
      if [[ "$detail" == *"N/A-HW-MISSING"* ]]; then
        printf -- "- %s | %s | %s\n" "$gate" "$item" "$detail" >> "$RISKS_FILE"
      fi
      ;;
    BLOCKED)
      blocked_count=$((blocked_count + 1))
      printf -- "- %s | %s | %s\n" "$gate" "$item" "$detail" >> "$BLOCKERS_FILE"
      ;;
  esac

  printf -- "- %s | %s | %s | %s\n" "$status" "$gate" "$item" "$detail" >> "$REPORT"
}

run_cmd() {
  local gate="$1"
  local item="$2"
  local cwd="$3"
  local cmd="$4"
  local gate_key="${gate// /}"
  local log="$OUT_DIR/${gate_key}_${item}.log"
  local rc

  if [ -n "$cwd" ]; then
    log_cmd "$gate" "$item" "cd \"$cwd\" && $cmd"
    (cd "$cwd" && bash -lc "$cmd") >"$log" 2>&1
    rc=$?
  else
    log_cmd "$gate" "$item" "$cmd"
    bash -lc "$cmd" >"$log" 2>&1
    rc=$?
  fi

  if [ $rc -eq 0 ]; then
    record "PASS" "$gate" "$item" "ok (log: $(rel_path "$log"))"
  else
    record "FAIL" "$gate" "$item" "rc=$rc (log: $(rel_path "$log"))"
  fi

  return $rc
}

code_expected() {
  local code="$1"
  local expected="$2"
  local token
  IFS=',' read -r -a token_list <<< "$expected"
  for token in "${token_list[@]}"; do
    if [ "$code" = "$token" ]; then
      return 0
    fi
  done
  return 1
}

api_call() {
  local gate="$1"
  local item="$2"
  local method="$3"
  local path="$4"
  local body="$5"
  local expected_codes="$6"
  local gate_key="${gate// /}"
  local rc

  API_OUT="$OUT_DIR/${gate_key}_${item}.json"
  API_HTTP="$OUT_DIR/${gate_key}_${item}.http"
  API_LOG="$OUT_DIR/${gate_key}_${item}.curl.log"

  if [ -n "$body" ]; then
    log_cmd "$gate" "$item" "curl --noproxy '*' -sS -m 45 -X $method '$BASE_URL$path' -H 'Content-Type: application/json' -d '$body'"
    API_CODE="$(curl --noproxy "*" -sS -m 45 -o "$API_OUT" -w "%{http_code}" -X "$method" "$BASE_URL$path" -H "Content-Type: application/json" -d "$body" 2>"$API_LOG")"
    rc=$?
  else
    log_cmd "$gate" "$item" "curl --noproxy '*' -sS -m 45 -X $method '$BASE_URL$path'"
    API_CODE="$(curl --noproxy "*" -sS -m 45 -o "$API_OUT" -w "%{http_code}" -X "$method" "$BASE_URL$path" 2>"$API_LOG")"
    rc=$?
  fi

  echo "$API_CODE" > "$API_HTTP"

  if [ $rc -ne 0 ]; then
    return 10
  fi
  if ! code_expected "$API_CODE" "$expected_codes"; then
    return 11
  fi
  return 0
}

is_hw_missing() {
  local primary="$1"
  local secondary="${2:-}"
  "$PYTHON_BIN" - "$primary" "$secondary" <<'PY'
import sys
from pathlib import Path

blob_parts = []
for p in sys.argv[1:]:
    if p and Path(p).exists():
        blob_parts.append(Path(p).read_text(encoding="utf-8", errors="ignore").lower())

blob = "\n".join(blob_parts)
keywords = [
    "n/a-hw-missing",
    "gpio not available",
    "gpiomem",
    "failed to add edge detection",
    "pigpio",
    "i2c",
    "smbus",
    "oled",
    "unknown pcm",
    "cannot open device",
    "audio device",
    "microphone",
    "no microphone",
    "device not found",
    "e_dependency_missing",
]

raise SystemExit(0 if any(k in blob for k in keywords) else 1)
PY
}

stop_service() {
  if [ -n "${service_pid:-}" ]; then
    kill "$service_pid" >/dev/null 2>&1 || true
    wait "$service_pid" >/dev/null 2>&1 || true
  fi
}

trap stop_service EXIT

cat > "$REPORT" <<HEAD
# mcar Release Gate Run ($STAMP)

- Root: $ROOT_DIR
- Output: $(rel_path "$OUT_DIR")
- Contract precedence: modules/*/capabilities.json > modules/robot_service/api.py > docs/TESTING.md

## Results
HEAD

# Gate P ----------------------------------------------------------------------
if command -v node >/dev/null 2>&1; then
  record "NA" "Gate P" "node_version" "$(node --version) (not required by Python runtime)"
else
  record "NA" "Gate P" "node_version" "not installed (not required by Python runtime)"
fi

"$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
if [ $? -eq 0 ]; then
  record "PASS" "Gate P" "python_version" "$("$PYTHON_BIN" --version 2>/dev/null)"
else
  record "FAIL" "Gate P" "python_version" "python >=3.11 required, got $("$PYTHON_BIN" --version 2>/dev/null)"
  add_retest "升级 Python 至 >=3.11 后重跑 Gate P/A/B/C。"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ]; then
  record "PASS" "Gate P" "env_file" ".ai_pet_env present"
else
  record "FAIL" "Gate P" "env_file" ".ai_pet_env missing"
  add_retest "补齐 /root/mcar/.ai_pet_env 并配置必要密钥后重跑。"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ] && grep -Eq '^(export[[:space:]]+)?(GEMINI_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY)="?[^"]+"?$' "$ROOT_DIR/.ai_pet_env" && ! grep -Eq 'your_.*here' "$ROOT_DIR/.ai_pet_env"; then
  record "PASS" "Gate P" "llm_key" "configured"
else
  record "NA" "Gate P" "llm_key" "N/A-KEY-MISSING (chat uses local degradation response)"
  add_retest "配置 Pydantic AI 支持的 provider key 后补测真实 LLM 对话能力。"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ] && grep -Eq '^(export[[:space:]]+)?VOICE_WAKE_PROVIDER="?[^"]+"?$' "$ROOT_DIR/.ai_pet_env" && ! grep -Eq 'VOICE_WAKE_PROVIDER="?none"?$' "$ROOT_DIR/.ai_pet_env"; then
  record "PASS" "Gate P" "wake_provider" "configured"
elif [ -f "$ROOT_DIR/.ai_pet_env" ] && grep -Eq '^(export[[:space:]]+)?PICOVOICE_ACCESS_KEY="?[^"]+"?$' "$ROOT_DIR/.ai_pet_env" && ! grep -Eq 'your_.*here' "$ROOT_DIR/.ai_pet_env"; then
  record "PASS" "Gate P" "wake_provider" "picovoice configured"
else
  record "NA" "Gate P" "wake_provider" "N/A-WAKE-PROVIDER-MISSING (wake-word tests skipped; risk: continuous wake-word loop unverified)"
  add_retest "配置 VOICE_WAKE_PROVIDER=openwakeword 后补测 voice.listen_start/stop。"
fi

if [ -d "$ROOT_DIR/data" ]; then
  log_cmd "Gate P" "data_backup" "tar -czf \"$OUT_DIR/data-backup.tgz\" -C \"$ROOT_DIR\" data"
  tar -czf "$OUT_DIR/data-backup.tgz" -C "$ROOT_DIR" data >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    record "PASS" "Gate P" "data_backup" "created $(rel_path "$OUT_DIR/data-backup.tgz")"
  else
    record "FAIL" "Gate P" "data_backup" "failed to create backup"
    add_retest "检查 data 目录权限后重跑 Gate P。"
  fi
else
  record "NA" "Gate P" "data_backup" "N/A-DATA-MISSING"
fi

run_cmd "Gate P" "contract_motion_duration_ms" "$ROOT_DIR" \
  "\"$PYTHON_BIN\" -c 'import json,sys; d=json.load(open(\"modules/motion/capabilities.json\")); m={c[\"capability_id\"]:c for c in d}; req=[\"tool.motion.forward\",\"tool.motion.backward\",\"tool.motion.turn_left\",\"tool.motion.turn_right\"]; miss=[cid for cid in req if \"duration_ms\" not in m[cid][\"inputs_schema\"][\"properties\"]]; sys.exit(1 if miss else 0)'" || add_retest "补齐 tool.motion.* 输入字段 duration_ms（按 capabilities.json）后重跑。"

run_cmd "Gate P" "contract_voice_timeout_s" "$ROOT_DIR" \
  "\"$PYTHON_BIN\" -c 'import json,sys; d=json.load(open(\"modules/voice/capabilities.json\")); c=[x for x in d if x[\"capability_id\"]==\"tool.voice.recognize\"][0]; props=c[\"inputs_schema\"].get(\"properties\",{}); sys.exit(0 if \"timeout_s\" in props else 1)'" || add_retest "补齐 tool.voice.recognize 输入字段 timeout_s 后重跑。"

run_cmd "Gate P" "contract_infrared_output_fields" "$ROOT_DIR" \
  "\"$PYTHON_BIN\" -c 'import json,sys; d=json.load(open(\"modules/sensor/capabilities.json\")); c=[x for x in d if x[\"capability_id\"]==\"tool.sensor.infrared\"][0]; req=set(c[\"outputs_schema\"].get(\"required\",[])); props=set(c[\"outputs_schema\"].get(\"properties\",{}).keys()); need={\"left_obstacle\",\"right_obstacle\"}; sys.exit(0 if need.issubset(req) and need.issubset(props) else 1)'" || add_retest "补齐 tool.sensor.infrared 输出字段 left_obstacle/right_obstacle 后重跑。"

run_cmd "Gate P" "api_chat_text_required" "$ROOT_DIR" \
  "\"$PYTHON_BIN\" -c 'from pathlib import Path; import sys; s=Path(\"modules/robot_service/models.py\").read_text(); sys.exit(0 if \"class ChatRequest\" in s and \"text: str\" in s else 1)'" || add_retest "修复 /api/chat 对 text 字段的校验逻辑后重跑。"

if run_cmd "Gate P" "docs_low_priority_reference" "$ROOT_DIR" \
  "\"$PYTHON_BIN\" -c 'from pathlib import Path; import sys; s=Path(\"docs/TESTING.md\").read_text(); need=[\"\\\"text\\\"\", \"duration_ms\", \"timeout_s\", \"left_obstacle\", \"right_obstacle\"]; sys.exit(0 if all(k in s for k in need) else 1)'"; then
  record "PASS" "Gate P" "contract_precedence" "runtime checks aligned to modules > robot_service api > docs"
else
  record "NA" "Gate P" "contract_precedence" "docs partially out-of-date, runtime checks still enforce modules > robot_service api"
fi

# Gate A ----------------------------------------------------------------------
if [ "$SKIP_GATE_A" = "1" ]; then
  record "NA" "Gate A" "skip_gate_a" "SKIP_GATE_A=1 (risk: dependency/build/test baseline not revalidated in this run)"
  add_retest "在系统负载可控时补跑完整 Gate A（安装/构建/测试）。"
else
  if [ -d "$VENV_DIR" ]; then
    record "PASS" "Gate A" "python_venv" "reused existing $(rel_path "$VENV_DIR")"
  else
    run_cmd "Gate A" "python_venv" "$ROOT_DIR" "\"$PYTHON_BIN\" -m venv \"$VENV_DIR\"" || gatea_fail=1
  fi

  run_cmd "Gate A" "modules_install" "$ROOT_DIR/modules" "\"$VENV_DIR/bin/python\" -m pip install -e \".[hw,voice,display,dev]\" || \"$VENV_DIR/bin/python\" -m pip install -e \".[dev]\"" || gatea_fail=1
  run_cmd "Gate A" "robot_service_compile" "$ROOT_DIR" "\"$VENV_DIR/bin/python\" -m compileall modules/robot_service" || gatea_fail=1
  run_cmd "Gate A" "modules_pytest" "$ROOT_DIR/modules" "\"$VENV_DIR/bin/python\" -m pytest -q" || gatea_fail=1

  if [ $gatea_fail -ne 0 ]; then
    add_retest "先修复 Gate A 的构建/测试失败，再执行 Gate B/C 真机验收。"
  fi
fi

# Gate B ----------------------------------------------------------------------
if [ $gatea_fail -ne 0 ]; then
  record "BLOCKED" "Gate B" "service_start" "blocked by Gate A failures"
  add_retest "Gate A 全部通过后重新启动 Gate B。"
else
  service_log="$OUT_DIR/GateB_service.log"
  service_pid_file="$OUT_DIR/GateB_service.pid"
  log_cmd "Gate B" "service_start" "cd \"$ROOT_DIR/modules\" && PATH=\"$VENV_DIR/bin:\$PATH\" \"$VENV_DIR/bin/python\" -m robot_service --mock"
  (
    cd "$ROOT_DIR/modules"
    PATH="$VENV_DIR/bin:$PATH" "$VENV_DIR/bin/python" -m robot_service --mock >"$service_log" 2>&1 &
    echo $! > "$service_pid_file"
  )
  service_pid="$(cat "$service_pid_file")"

  started=0
  for _ in $(seq 1 30); do
    api_call "Gate B" "status_probe" "GET" "/api/status" "" "200"
    rc=$?
    if [ $rc -eq 0 ]; then
      started=1
      break
    fi
    sleep 1
  done

  if [ $started -eq 1 ]; then
    service_started=1
    record "PASS" "Gate B" "service_start" "service reachable at /api/status (log: $(rel_path "$service_log"))"
  else
    record "FAIL" "Gate B" "service_start" "service did not become ready (log: $(rel_path "$service_log"))"
    add_retest "检查 GateB_service.log 启动错误后重跑 Gate B/C。"
  fi
fi

if [ $service_started -eq 1 ]; then
  for ep in status modules capabilities health watchdog metrics audit sessions rules/status; do
    item="api_${ep//\//_}"
    api_call "Gate B" "$item" "GET" "/api/$ep" "" "200"
    rc=$?
    if [ $rc -eq 0 ]; then
      record "PASS" "Gate B" "$item" "http=200 (json: $(rel_path "$API_OUT"))"
    elif [ $rc -eq 10 ]; then
      record "FAIL" "Gate B" "$item" "curl failed (log: $(rel_path "$API_LOG"))"
      add_retest "排查 /api/$ep 请求失败后重跑 Gate B。"
    else
      record "FAIL" "Gate B" "$item" "http=$API_CODE expected 200 (json: $(rel_path "$API_OUT"))"
      add_retest "修复 /api/$ep 返回码后重跑 Gate B。"
    fi
  done

  api_call "Gate B" "contract_chat_text_positive" "POST" "/api/chat" '{"text":"验收检查：请回复ok"}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if isinstance(j, dict) and "response" in j else 1)
PY
  then
    record "PASS" "Gate B" "contract_chat_text_positive" "accepted /api/chat text (json: $(rel_path "$API_OUT"))"
  else
    if [ $rc -eq 10 ]; then
      record "FAIL" "Gate B" "contract_chat_text_positive" "curl failed (log: $(rel_path "$API_LOG"))"
    elif [ $rc -eq 11 ]; then
      record "FAIL" "Gate B" "contract_chat_text_positive" "http=$API_CODE expected 200 (json: $(rel_path "$API_OUT"))"
    else
      record "FAIL" "Gate B" "contract_chat_text_positive" "response missing 'response' field (json: $(rel_path "$API_OUT"))"
    fi
    add_retest "修复 /api/chat 正向 text 调用后重跑。"
  fi

  api_call "Gate B" "contract_voice_run_once_positive" "POST" "/api/voice/run_once" '{"source":"gate_b"}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if isinstance(j, dict) and "ok" in j else 1)
PY
  then
    record "PASS" "Gate B" "contract_voice_run_once_positive" "accepted /api/voice/run_once source payload (json: $(rel_path "$API_OUT"))"
  else
    if [ $rc -eq 10 ]; then
      record "FAIL" "Gate B" "contract_voice_run_once_positive" "curl failed (log: $(rel_path "$API_LOG"))"
    elif [ $rc -eq 11 ]; then
      record "FAIL" "Gate B" "contract_voice_run_once_positive" "http=$API_CODE expected 200 (json: $(rel_path "$API_OUT"))"
    else
      record "FAIL" "Gate B" "contract_voice_run_once_positive" "response missing 'ok' field (json: $(rel_path "$API_OUT"))"
    fi
    add_retest "修复 /api/voice/run_once 正向 source 调用后重跑。"
  fi

  api_call "Gate B" "contract_chat_text_negative" "POST" "/api/chat" '{"message":"wrong"}' "400,422"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(0 if "text" in blob else 1)
PY
  then
    record "PASS" "Gate B" "contract_chat_text_negative" "non-text payload rejected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "contract_chat_text_negative" "chat wrong-field payload not rejected as expected (json: $(rel_path "$API_OUT"))"
    add_retest "确保 /api/chat 仅接受 text 字段并返回 400/422。"
  fi

  api_call "Gate B" "contract_motion_duration_positive" "POST" "/api/invoke" '{"capability_id":"tool.motion.turn_left","input":{"speed":0,"duration_ms":120}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(1 if "e_input_schema" in blob else 0)
PY
  then
    record "PASS" "Gate B" "contract_motion_duration_positive" "duration_ms accepted (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "contract_motion_duration_positive" "duration_ms call rejected by schema (json: $(rel_path "$API_OUT"))"
    add_retest "修复 tool.motion.* 对 duration_ms 的参数校验后重跑。"
  fi

  api_call "Gate B" "contract_motion_duration_negative" "POST" "/api/invoke" '{"capability_id":"tool.motion.turn_left","input":{"speed":0,"duration":120}}' "200,400"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(0 if "e_input_schema" in blob or "validation failed" in blob else 1)
PY
  then
    record "PASS" "Gate B" "contract_motion_duration_negative" "wrong field rejected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "contract_motion_duration_negative" "wrong field duration not rejected (json: $(rel_path "$API_OUT"))"
    add_retest "确保 tool.motion.* 不接受 duration，仅接受 duration_ms。"
  fi

  api_call "Gate B" "contract_voice_timeout_positive" "POST" "/api/invoke" '{"capability_id":"tool.voice.recognize","input":{"timeout_s":1}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(1 if "e_input_schema" in blob else 0)
PY
  then
    record "PASS" "Gate B" "contract_voice_timeout_positive" "timeout_s accepted (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "contract_voice_timeout_positive" "timeout_s call rejected by schema (json: $(rel_path "$API_OUT"))"
    add_retest "修复 tool.voice.recognize 对 timeout_s 的参数校验后重跑。"
  fi

  api_call "Gate B" "contract_voice_timeout_negative" "POST" "/api/invoke" '{"capability_id":"tool.voice.recognize","input":{"timeout":1}}' "200,400"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(0 if "e_input_schema" in blob or "validation failed" in blob else 1)
PY
  then
    record "PASS" "Gate B" "contract_voice_timeout_negative" "wrong field rejected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "contract_voice_timeout_negative" "wrong field timeout not rejected (json: $(rel_path "$API_OUT"))"
    add_retest "确保 tool.voice.recognize 不接受 timeout，仅接受 timeout_s。"
  fi

  api_call "Gate B" "contract_infrared_output" "POST" "/api/invoke" '{"capability_id":"tool.sensor.infrared","input":{}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
payload = j.get("data") or j.get("result") or {}
ok = j.get("success") is True and isinstance(payload, dict) and "left_obstacle" in payload and "right_obstacle" in payload
raise SystemExit(0 if ok else 1)
PY
  then
    record "PASS" "Gate B" "contract_infrared_output" "left_obstacle/right_obstacle present (json: $(rel_path "$API_OUT"))"
  else
    if [ $rc -eq 10 ]; then
      record "FAIL" "Gate B" "contract_infrared_output" "curl failed (log: $(rel_path "$API_LOG"))"
      add_retest "排查 sensor 模块调用失败后重跑 Gate B。"
    elif is_hw_missing "$API_OUT" "$API_LOG"; then
      record "NA" "Gate B" "contract_infrared_output" "N/A-HW-MISSING (risk: obstacle detection path unverified)"
      add_retest "修复红外传感器硬件连接后补测 tool.sensor.infrared。"
    else
      record "FAIL" "Gate B" "contract_infrared_output" "missing left_obstacle/right_obstacle (json: $(rel_path "$API_OUT"))"
      add_retest "修复 tool.sensor.infrared 输出字段后重跑。"
    fi
  fi

  api_call "Gate B" "negative_invalid_capability" "POST" "/api/invoke" '{"capability_id":"tool.invalid.not_exist","input":{}}' "200,400,500"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if j.get("success") is False else 1)
PY
  then
    record "PASS" "Gate B" "negative_invalid_capability" "rejected as expected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "negative_invalid_capability" "invalid capability not rejected (json: $(rel_path "$API_OUT"))"
    add_retest "修复不存在 capability_id 的拒绝路径后重跑。"
  fi

  api_call "Gate B" "negative_invalid_input" "POST" "/api/invoke" '{"capability_id":"tool.motion.forward","input":{"speed":101,"duration_ms":99999}}' "200,400"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(0 if "e_input_schema" in blob or j.get("success") is False else 1)
PY
  then
    record "PASS" "Gate B" "negative_invalid_input" "invalid input rejected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "negative_invalid_input" "out-of-bound input not rejected (json: $(rel_path "$API_OUT"))"
    add_retest "修复输入边界校验后重跑 Gate B。"
  fi

  api_call "Gate B" "negative_invalid_mode" "POST" "/api/mode" '{"mode":"turbo"}' "400,422"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(0 if "mode" in blob else 1)
PY
  then
    record "PASS" "Gate B" "negative_invalid_mode" "invalid mode rejected (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "negative_invalid_mode" "invalid mode not rejected (json: $(rel_path "$API_OUT"))"
    add_retest "修复 /api/mode 非法模式拒绝路径后重跑 Gate B。"
  fi

  api_call "Gate B" "watchdog_stability" "GET" "/api/watchdog" "" "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
blob = json.dumps(j, ensure_ascii=False).lower()
raise SystemExit(1 if '"permanentlyfailed": true' in blob else 0)
PY
  then
    record "PASS" "Gate B" "watchdog_stability" "no permanentlyFailed=true (json: $(rel_path "$API_OUT"))"
  else
    record "FAIL" "Gate B" "watchdog_stability" "permanentlyFailed=true or watchdog parse error (json: $(rel_path "$API_OUT"))"
    add_retest "排查模块崩溃/重启问题后重跑 Gate B/C。"
  fi
fi

# Gate C ----------------------------------------------------------------------
if [ $service_started -ne 1 ]; then
  record "BLOCKED" "Gate C" "hardware_validation" "blocked because Gate B service is unavailable"
  add_retest "先恢复服务启动，再执行 Gate C 真机检查。"
else
  if [ "$IGNORE_BUTTON_HW" = "1" ]; then
    record "NA" "Gate C" "button_physical_estop" "N/A-HW-MISSING (waived by user request; risk: physical e-stop path unverified, fallback to /api/stop only)"
    add_retest "后续恢复物理 button 后，补测 GPIO17 急停链路。"
  else
    api_call "Gate C" "button_physical_estop" "POST" "/api/invoke" '{"capability_id":"tool.button.status","input":{}}' "200"
    rc=$?
    if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
payload = j.get("data") or j.get("result") or {}
ok = j.get("success") is True and isinstance(payload, dict) and "pressed" in payload
raise SystemExit(0 if ok else 1)
PY
    then
      record "PASS" "Gate C" "button_physical_estop" "button status readable (json: $(rel_path "$API_OUT"))"
    elif is_hw_missing "$API_OUT" "$API_LOG"; then
      record "NA" "Gate C" "button_physical_estop" "N/A-HW-MISSING (risk: physical e-stop path unverified)"
      add_retest "修复 button GPIO 边沿检测后补测。"
    else
      record "FAIL" "Gate C" "button_physical_estop" "button status check failed (json: $(rel_path "$API_OUT"))"
      add_retest "修复 button 模块后重跑 Gate C。"
    fi
  fi

  api_call "Gate C" "sensor_infrared_hw" "POST" "/api/invoke" '{"capability_id":"tool.sensor.infrared","input":{}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
payload = j.get("data") or j.get("result") or {}
ok = j.get("success") is True and isinstance(payload, dict) and "left_obstacle" in payload and "right_obstacle" in payload
raise SystemExit(0 if ok else 1)
PY
  then
    record "PASS" "Gate C" "sensor_infrared_hw" "infrared hardware response valid (json: $(rel_path "$API_OUT"))"
  elif is_hw_missing "$API_OUT" "$API_LOG"; then
    record "NA" "Gate C" "sensor_infrared_hw" "N/A-HW-MISSING (risk: obstacle detection path unverified)"
    add_retest "恢复红外传感器后补测 Gate C sensor_infrared_hw。"
  else
    record "FAIL" "Gate C" "sensor_infrared_hw" "infrared response invalid (json: $(rel_path "$API_OUT"))"
    add_retest "修复 sensor.infrared 响应结构后重跑 Gate C。"
  fi

  api_call "Gate C" "motion_turn_left_hw" "POST" "/api/invoke" '{"capability_id":"tool.motion.turn_left","input":{"speed":0,"duration_ms":150}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if j.get("success") is True else 1)
PY
  then
    record "PASS" "Gate C" "motion_turn_left_hw" "motion capability executed (json: $(rel_path "$API_OUT"))"
  elif is_hw_missing "$API_OUT" "$API_LOG"; then
    record "NA" "Gate C" "motion_turn_left_hw" "N/A-HW-MISSING (risk: wheel control path unverified)"
    add_retest "恢复运动驱动硬件后补测 Gate C motion_turn_left_hw。"
  else
    record "FAIL" "Gate C" "motion_turn_left_hw" "motion capability failed (json: $(rel_path "$API_OUT"))"
    add_retest "修复 motion 模块执行失败后重跑 Gate C。"
  fi

  api_call "Gate C" "display_show_text_hw" "POST" "/api/invoke" '{"capability_id":"tool.display.show_text","input":{"text":"GateC display smoke"}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if j.get("success") is True else 1)
PY
  then
    record "PASS" "Gate C" "display_show_text_hw" "display capability executed (json: $(rel_path "$API_OUT"))"
  elif is_hw_missing "$API_OUT" "$API_LOG"; then
    record "NA" "Gate C" "display_show_text_hw" "N/A-HW-MISSING (risk: OLED output path unverified)"
    add_retest "恢复 OLED 硬件后补测 Gate C display_show_text_hw。"
  else
    record "FAIL" "Gate C" "display_show_text_hw" "display capability failed (json: $(rel_path "$API_OUT"))"
    add_retest "修复 display 模块执行失败后重跑 Gate C。"
  fi

  api_call "Gate C" "voice_recognize_hw" "POST" "/api/invoke" '{"capability_id":"tool.voice.recognize","input":{"timeout_s":1}}' "200"
  rc=$?
  if [ $rc -eq 0 ] && "$PYTHON_BIN" - "$API_OUT" <<'PY'
import json, sys
j = json.load(open(sys.argv[1], encoding="utf-8"))
if j.get("success") is not True:
    raise SystemExit(1)
payload = j.get("data") or j.get("result") or {}
raise SystemExit(0 if isinstance(payload, dict) and "ok" in payload else 1)
PY
  then
    record "PASS" "Gate C" "voice_recognize_hw" "voice recognize call executed (json: $(rel_path "$API_OUT"))"
  elif is_hw_missing "$API_OUT" "$API_LOG"; then
    record "NA" "Gate C" "voice_recognize_hw" "N/A-HW-MISSING (risk: microphone/ASR path unverified)"
    add_retest "恢复麦克风/语音依赖后补测 Gate C voice_recognize_hw。"
  else
    record "FAIL" "Gate C" "voice_recognize_hw" "voice recognize failed (json: $(rel_path "$API_OUT"))"
    add_retest "修复 voice.recognize 运行失败后重跑 Gate C。"
  fi
fi

# Summary ---------------------------------------------------------------------
{
  echo
  echo "## Summary"
  echo
  echo "- PASS: $pass_count"
  echo "- FAIL: $fail_count"
  echo "- NA: $na_count"
  echo "- BLOCKED: $blocked_count"
  echo
  echo "## Blocking Issues"
  echo
  if [ -s "$BLOCKERS_FILE" ]; then
    cat "$BLOCKERS_FILE"
  else
    echo "- none"
  fi
  echo
  echo "## Hardware Risks"
  echo
  if [ -s "$RISKS_FILE" ]; then
    cat "$RISKS_FILE"
  else
    echo "- none"
  fi
  echo
  echo "## Retest Suggestions"
  echo
  if [ -s "$RETEST_FILE" ]; then
    cat "$RETEST_FILE"
  else
    echo "- none"
  fi
  echo
  if [ $fail_count -eq 0 ] && [ $blocked_count -eq 0 ]; then
    echo "**Decision: GO**"
  else
    echo "**Decision: NO-GO**"
  fi
} >> "$REPORT"

echo "Release gate report generated: $REPORT"
