"""Tests for the Pi voice update deployment helper."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT = ROOT_DIR / "scripts" / "deploy_pi_voice_update.sh"


def test_pi_voice_deploy_script_syncs_required_voice_files() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    required_paths = [
        "modules/robot_service/api.py",
        "modules/robot_service/command_parser.py",
        "modules/robot_service/voice_session.py",
        "modules/robot_service/adapters.py",
        "modules/voice/asr.py",
        "modules/voice/driver.py",
        "modules/voice/module.py",
        "modules/voice/wake_word.py",
        "modules/voice/capabilities.json",
        "scripts/voice_e2e_probe.py",
    ]
    for path in required_paths:
        assert path in script


def test_pi_voice_deploy_script_restarts_and_verifies_service() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'PI_SERVICE="${PI_SERVICE:-mcar}"' in script
    assert "systemctl restart '$PI_SERVICE'" in script
    assert "systemctl is-active '$PI_SERVICE'" in script
    assert "wait_for_api" in script
    assert "/api/status" in script
    assert "test_robot_service_voice_session.py" in script
    assert "test_voice_e2e_probe_script.py" in script
    assert "voice_e2e_probe.py" in script
    assert "--base-url" in script
