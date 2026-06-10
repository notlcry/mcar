#!/usr/bin/env bash
#
# mcar installation script for Raspberry Pi.
#
# Usage:
#   chmod +x deploy/install.sh
#   ./deploy/install.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/mcar.service"

echo "=== mcar Installation ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# ─── 1. Check Python3 ─────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python3 not found."
  echo "Install with: sudo apt install -y python3 python3-pip python3-venv"
  exit 1
fi
echo "Python3: $(python3 --version)"

# ─── 2. Check system dependencies ─────────────────────
echo ""
echo "--- Checking system dependencies ---"
MISSING_PKGS=()
SYS_PKGS=(portaudio19-dev libjpeg-dev i2c-tools python3-pip python3-venv)

for pkg in "${SYS_PKGS[@]}"; do
  if ! dpkg -s "$pkg" &>/dev/null; then
    MISSING_PKGS+=("$pkg")
  fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
  echo "Missing system packages: ${MISSING_PKGS[*]}"
  read -p "Install them now? (requires sudo) [Y/n] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    sudo apt update
    sudo apt install -y "${MISSING_PKGS[@]}"
    echo "System packages installed."
  else
    echo "WARNING: Skipped. Some modules may not work without: ${MISSING_PKGS[*]}"
  fi
else
  echo "All system packages present."
fi

# ─── 3. Check I2C enabled ─────────────────────────────
echo ""
echo "--- Checking I2C ---"
if [ -e /dev/i2c-1 ]; then
  echo "I2C bus 1: enabled"
  if command -v i2cdetect &>/dev/null; then
    echo "  Detected devices:"
    i2cdetect -y 1 2>/dev/null | grep -E "^\d" || true
  fi
else
  echo "WARNING: I2C not enabled. OLED and motor controller won't work."
  echo "  Enable with: sudo raspi-config → Interface Options → I2C → Enable"
  echo "  Then reboot."
fi

# ─── 4. Install Python dependencies ──────────────────
echo ""
echo "--- Installing Python dependencies ---"
python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/python" -m pip install --upgrade pip
cd "$PROJECT_DIR/modules"

# Detect platform for correct extras
if [ -f /proc/device-tree/model ] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
  echo "Raspberry Pi detected — installing all hardware extras."
  "$PROJECT_DIR/.venv/bin/python" -m pip install -e ".[hw,voice,display,dev]"
else
  echo "Non-Pi platform — installing dev extras only (mock mode)."
  "$PROJECT_DIR/.venv/bin/python" -m pip install -e ".[dev]"
fi

# ─── 5. Create data directory ─────────────────────────
echo ""
echo "--- Creating data directory ---"
mkdir -p "$PROJECT_DIR/data"

# ─── 6. Check environment file ────────────────────────
if [ ! -f "$PROJECT_DIR/.ai_pet_env" ]; then
  echo ""
  echo "WARNING: .ai_pet_env not found."
  echo "Copy the template and fill in your API keys:"
  echo "  cp $PROJECT_DIR/.ai_pet_env.example $PROJECT_DIR/.ai_pet_env"
  echo "  nano $PROJECT_DIR/.ai_pet_env"
fi

# ─── 7. Post-install verification ────────────────────
echo ""
echo "--- Verifying installation ---"
VERIFY_OK=true

# Check Python Robot Service importable
if "$PROJECT_DIR/.venv/bin/python" -c "import robot_service; print('  robot_service import ok')" 2>/dev/null; then
  echo "[OK] robot_service importable"
else
  echo "[FAIL] robot_service not importable"
  VERIFY_OK=false
fi

# Check FastAPI importable
if "$PROJECT_DIR/.venv/bin/python" -c "import fastapi; print(f'  fastapi {fastapi.__version__}')" 2>/dev/null; then
  echo "[OK] fastapi importable"
else
  echo "[FAIL] fastapi not importable"
  VERIFY_OK=false
fi

# Check data directory
if [ -d "$PROJECT_DIR/data" ]; then
  echo "[OK] data/ directory exists"
else
  echo "[FAIL] data/ directory missing"
  VERIFY_OK=false
fi

# Check env file
if [ -f "$PROJECT_DIR/.ai_pet_env" ]; then
  echo "[OK] .ai_pet_env exists"
else
  echo "[WARN] .ai_pet_env not configured yet"
fi

if [ "$VERIFY_OK" = false ]; then
  echo ""
  echo "WARNING: Some verification checks failed. Review the errors above."
fi

# ─── 8. Install systemd service (optional) ──────────
echo ""
read -p "Install systemd service for auto-start? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Update WorkingDirectory in service file
  sed "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" "$SERVICE_FILE" |
  sed "s|Environment=PATH=.*|Environment=PATH=$PROJECT_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin|g" |
  sed "s|Environment=VIRTUAL_ENV=.*|Environment=VIRTUAL_ENV=$PROJECT_DIR/.venv|g" |
  sed "s|Environment=MCAR_PROJECT_DIR=.*|Environment=MCAR_PROJECT_DIR=$PROJECT_DIR|g" |
  sed "s|Environment=MCAR_ENV_FILE=.*|Environment=MCAR_ENV_FILE=$PROJECT_DIR/.ai_pet_env|g" |
  sed "s|User=.*|User=$(whoami)|g" |
  sed "s|Group=.*|Group=$(id -gn)|g" |
  sudo tee /etc/systemd/system/mcar.service > /dev/null

  sudo systemctl daemon-reload
  sudo systemctl enable mcar
  echo "Service installed and enabled."
  echo "Start with: sudo systemctl start mcar"
  echo "View logs:  journalctl -u mcar -f"
else
  echo "Skipped systemd installation."
  echo "Start manually: $PROJECT_DIR/.venv/bin/python -m robot_service --mock"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Configure API key:  nano $PROJECT_DIR/.ai_pet_env"
echo "  2. Start service:      sudo systemctl start mcar"
echo "  3. Check status:       curl http://localhost:8080/api/status"
echo "  4. View logs:          journalctl -u mcar -f"
