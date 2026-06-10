"""Tests for release gate contract coverage."""

from __future__ import annotations

from pathlib import Path
import re


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_release_gate_checks_voice_run_once_contract() -> None:
    script = (ROOT_DIR / "scripts" / "run_release_gate.sh").read_text(encoding="utf-8")

    assert 'contract_voice_run_once_positive' in script
    assert '"/api/voice/run_once"' in script
    assert '{"source":"gate_b"}' in script


def test_release_gate_allows_python_and_venv_overrides() -> None:
    script = (ROOT_DIR / "scripts" / "run_release_gate.sh").read_text(encoding="utf-8")

    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in script
    assert 'VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv-gate}"' in script
    assert '"$PYTHON_BIN" --version' in script
    assert '\\"$PYTHON_BIN\\" -m venv \\"$VENV_DIR\\"' in script


def test_release_gate_motion_smokes_do_not_reuse_idempotency_key() -> None:
    script = (ROOT_DIR / "scripts" / "run_release_gate.sh").read_text(encoding="utf-8")
    gate_b = re.search(
        r'contract_motion_duration_positive".*?"duration_ms":(\d+)',
        script,
    )
    gate_c = re.search(
        r'motion_turn_left_hw".*?"duration_ms":(\d+)',
        script,
    )

    assert gate_b is not None
    assert gate_c is not None
    assert gate_b.group(1) != gate_c.group(1)
