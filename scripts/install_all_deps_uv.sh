#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/root/mcar"
VENV_DIR="$ROOT_DIR/.venv"
LOG_FILE="$ROOT_DIR/install-deps-$(date +%Y-%m-%d_%H-%M-%S).log"

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "ERROR: root directory not found: $ROOT_DIR" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv not found in PATH" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found in PATH" >&2
  exit 1
fi

# Keep process priority lower to reduce chance of starving SSH/network.
# Ensure we only re-exec once to avoid recursion loops.
if [[ "${MCAR_DEPS_CHILD:-0}" != "1" ]]; then
  if command -v ionice >/dev/null 2>&1; then
    exec env MCAR_DEPS_CHILD=1 ionice -c2 -n7 nice -n 10 bash "$0" "$@"
  elif command -v nice >/dev/null 2>&1; then
    exec env MCAR_DEPS_CHILD=1 nice -n 10 bash "$0" "$@"
  fi
fi

cd "$ROOT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[INFO] root: $ROOT_DIR"
echo "[INFO] log : $LOG_FILE"
echo "[INFO] uv  : $(uv --version)"
echo "[INFO] npm : $(npm -v)"

echo "[STEP] Create/refresh venv: $VENV_DIR"
if [[ "${MCAR_VENV_CLEAR:-0}" == "1" ]]; then
  echo "[INFO] Recreating venv because MCAR_VENV_CLEAR=1"
  uv venv --clear "$VENV_DIR"
elif [[ -x "$VENV_DIR/bin/python" ]]; then
  echo "[INFO] Reusing existing venv: $VENV_DIR"
else
  uv venv "$VENV_DIR"
fi

echo "[STEP] Install Node dependencies (core)"
cd "$ROOT_DIR/core"
npm install --no-audit --no-fund

echo "[STEP] Install Python dependencies (modules: hw,voice,display,dev)"
cd "$ROOT_DIR/modules"
uv pip install --python "$VENV_DIR/bin/python" -e ".[hw,voice,display,dev]"

echo "[STEP] Verify key Python imports in venv"
"$VENV_DIR/bin/python" - <<'PY'
import importlib
mods = ["zmq", "RPi.GPIO", "smbus2", "speech_recognition", "luma.oled", "edge_tts", "pvporcupine", "pygame"]
failed = []
for m in mods:
    try:
        importlib.import_module(m)
        print(f"[OK] {m}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")
        failed.append(m)
if failed:
    raise SystemExit(f"Missing imports: {failed}")
PY

echo "[DONE] Dependency installation completed successfully."
echo "[DONE] Activate venv with: source $VENV_DIR/bin/activate"
echo "[DONE] Full log: $LOG_FILE"
