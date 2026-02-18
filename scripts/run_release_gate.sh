#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
OUT_DIR="$ROOT_DIR/docs/verification/run-$STAMP"
REPORT="$OUT_DIR/report.md"
mkdir -p "$OUT_DIR"

pass_count=0
fail_count=0
na_count=0
blocked_count=0

record() {
  local status="$1"
  local gate="$2"
  local item="$3"
  local detail="$4"

  case "$status" in
    PASS) pass_count=$((pass_count + 1)) ;;
    FAIL) fail_count=$((fail_count + 1)) ;;
    NA) na_count=$((na_count + 1)) ;;
    BLOCKED) blocked_count=$((blocked_count + 1)) ;;
  esac

  printf -- "- %s | %s | %s | %s\n" "$status" "$gate" "$item" "$detail" >> "$REPORT"
}

run_cmd() {
  local gate="$1"
  local item="$2"
  local cwd="$3"
  local cmd="$4"
  local log="$OUT_DIR/${gate}_${item}.log"
  local rc

  if [ -n "$cwd" ]; then
    (cd "$cwd" && bash -c "$cmd") >"$log" 2>&1
    rc=$?
  else
    bash -c "$cmd" >"$log" 2>&1
    rc=$?
  fi

  if [ $rc -eq 0 ]; then
    record "PASS" "$gate" "$item" "ok (log: ${log#$ROOT_DIR/})"
  else
    record "FAIL" "$gate" "$item" "rc=$rc (log: ${log#$ROOT_DIR/})"
  fi

  return $rc
}

cat > "$REPORT" <<HEAD
# mcar Release Gate Run ($STAMP)

- Root: $ROOT_DIR
- Output: ${OUT_DIR#$ROOT_DIR/}

## Results
HEAD

# Gate P
node_major="$(node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0)"
if [ "$node_major" -ge 20 ] 2>/dev/null; then
  record "PASS" "Gate P" "node_version" "$(node --version)"
else
  record "FAIL" "Gate P" "node_version" "node >=20 required"
fi

python_check_rc=0
python3 - <<'PY' >/dev/null 2>&1
import sys
sys.exit(0 if sys.version_info >= (3,11) else 1)
PY
python_check_rc=$?
if [ $python_check_rc -eq 0 ]; then
  record "PASS" "Gate P" "python_version" "$(python3 --version 2>/dev/null)"
else
  record "FAIL" "Gate P" "python_version" "python >=3.11 required, got $(python3 --version 2>/dev/null)"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ]; then
  record "PASS" "Gate P" "env_file" ".ai_pet_env present"
else
  record "FAIL" "Gate P" "env_file" ".ai_pet_env missing"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ] && grep -Eq '^(export[[:space:]]+)?GEMINI_API_KEY="?[^"]+"?$' "$ROOT_DIR/.ai_pet_env" && ! grep -Eq 'your_.*here' "$ROOT_DIR/.ai_pet_env"; then
  record "PASS" "Gate P" "gemini_key" "configured"
else
  record "FAIL" "Gate P" "gemini_key" "missing or template value"
fi

if [ -f "$ROOT_DIR/.ai_pet_env" ] && grep -Eq '^(export[[:space:]]+)?PICOVOICE_ACCESS_KEY="?[^"]+"?$' "$ROOT_DIR/.ai_pet_env" && ! grep -Eq 'your_.*here' "$ROOT_DIR/.ai_pet_env"; then
  record "PASS" "Gate P" "picovoice_key" "configured"
else
  record "NA" "Gate P" "picovoice_key" "N/A-KEY-MISSING"
fi

if [ -d "$ROOT_DIR/data" ]; then
  tar -czf "$OUT_DIR/data-backup.tgz" -C "$ROOT_DIR" data >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    record "PASS" "Gate P" "data_backup" "created docs/verification/.../data-backup.tgz"
  else
    record "FAIL" "Gate P" "data_backup" "failed to create backup"
  fi
else
  record "NA" "Gate P" "data_backup" "N/A-DATA-MISSING"
fi

# Gate A
run_cmd "GateA" "core_npm_install" "$ROOT_DIR/core" "npm install"
core_install_rc=$?
run_cmd "GateA" "core_build" "$ROOT_DIR/core" "npm run build"
core_build_rc=$?
run_cmd "GateA" "core_test" "$ROOT_DIR/core" "npm test"
run_cmd "GateA" "core_coverage_plugin" "$ROOT_DIR/core" "npm install --no-save @vitest/coverage-v8@3.2.4"
run_cmd "GateA" "core_test_coverage" "$ROOT_DIR/core" "npm run test:coverage"
run_cmd "GateA" "modules_install" "$ROOT_DIR/modules" "if command -v uv >/dev/null 2>&1; then uv pip install --python \"$(command -v python)\" \".[dev]\" || uv pip install --python \"$(command -v python)\" pyzmq pytest pytest-asyncio pytest-cov; else python -m pip install \".[dev]\" || python -m pip install pyzmq pytest pytest-asyncio pytest-cov; fi"
run_cmd "GateA" "modules_pytest" "$ROOT_DIR/modules" "pytest -q"

# Gate B
if [ $core_install_rc -ne 0 ] || [ $core_build_rc -ne 0 ] || [ ! -f "$ROOT_DIR/core/dist/index.js" ]; then
  record "BLOCKED" "Gate B" "service_start" "blocked by Gate A (core install/build)"
else
  service_log="$OUT_DIR/gateb_service.log"
  (
    cd "$ROOT_DIR/core"
    node dist/index.js >"$service_log" 2>&1 &
    echo $! > "$OUT_DIR/gateb_service.pid"
  )

  started=0
  for _ in $(seq 1 20); do
    if curl -sf "http://localhost:8080/api/status" > "$OUT_DIR/gateb_status.json" 2>/dev/null; then
      started=1
      break
    fi
    sleep 1
  done

  if [ $started -eq 1 ]; then
    record "PASS" "Gate B" "service_start" "service reachable at /api/status"
    for ep in status modules capabilities health watchdog metrics audit sessions rules/status; do
      if curl -sf "http://localhost:8080/api/$ep" > "$OUT_DIR/gateb_${ep//\//_}.json" 2>/dev/null; then
        record "PASS" "Gate B" "api_$ep" "200 OK"
      else
        record "FAIL" "Gate B" "api_$ep" "request failed"
      fi
    done

    if curl -sf -X POST "http://localhost:8080/api/invoke" \
      -H "Content-Type: application/json" \
      -d '{"capability_id":"tool.invalid.not_exist","input":{}}' \
      > "$OUT_DIR/gateb_invoke_invalid.json" 2>/dev/null; then
      if grep -q '"success":false' "$OUT_DIR/gateb_invoke_invalid.json"; then
        record "PASS" "Gate B" "negative_invalid_capability" "rejected as expected"
      else
        record "FAIL" "Gate B" "negative_invalid_capability" "did not return success=false"
      fi
    else
      record "FAIL" "Gate B" "negative_invalid_capability" "request failed"
    fi

    if curl -sf -X POST "http://localhost:8080/api/invoke" \
      -H "Content-Type: application/json" \
      -d '{"capability_id":"tool.motion.forward","input":{"speed":101,"duration_ms":99999}}' \
      > "$OUT_DIR/gateb_invoke_oob.json" 2>/dev/null; then
      if grep -q '"success":false' "$OUT_DIR/gateb_invoke_oob.json"; then
        record "PASS" "Gate B" "negative_invalid_input" "rejected as expected"
      else
        record "FAIL" "Gate B" "negative_invalid_input" "did not return success=false"
      fi
    else
      record "FAIL" "Gate B" "negative_invalid_input" "request failed"
    fi

    if curl -sf "http://localhost:8080/api/watchdog" > "$OUT_DIR/gateb_watchdog.json" 2>/dev/null; then
      if grep -q '"permanentlyFailed":true' "$OUT_DIR/gateb_watchdog.json"; then
        record "FAIL" "Gate B" "watchdog_stability" "permanentlyFailed=true found"
      else
        record "PASS" "Gate B" "watchdog_stability" "no permanentlyFailed=true"
      fi
    else
      record "FAIL" "Gate B" "watchdog_stability" "watchdog endpoint unavailable"
    fi
  else
    record "FAIL" "Gate B" "service_start" "service did not become ready"
  fi

  if [ -f "$OUT_DIR/gateb_service.pid" ]; then
    kill "$(cat "$OUT_DIR/gateb_service.pid")" >/dev/null 2>&1 || true
  fi
fi

# Gate C
record "NA" "Gate C" "raspberry_pi_full_validation" "N/A-HW-MISSING in local environment"

# Summary
{
  echo
  echo "## Summary"
  echo
  echo "- PASS: $pass_count"
  echo "- FAIL: $fail_count"
  echo "- NA: $na_count"
  echo "- BLOCKED: $blocked_count"
  echo
  if [ $fail_count -eq 0 ] && [ $blocked_count -eq 0 ]; then
    echo "**Decision: GO**"
  else
    echo "**Decision: NO-GO**"
  fi
} >> "$REPORT"

echo "Release gate report generated: $REPORT"
