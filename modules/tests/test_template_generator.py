"""Tests for the module template generator (scripts/new-module.sh)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "new-module.sh"
MODULES_DIR = PROJECT_ROOT / "modules"


def run_generator(module_id: str, description: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run the generator script and return the result."""
    cmd = [str(SCRIPT), module_id]
    if description:
        cmd.append(description)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def cleanup_module(module_id: str) -> None:
    """Remove generated module files."""
    module_dir = MODULES_DIR / module_id
    if module_dir.exists():
        shutil.rmtree(module_dir)
    test_file = MODULES_DIR / "tests" / f"test_{module_id}_module.py"
    if test_file.exists():
        test_file.unlink()


@pytest.fixture(autouse=True)
def cleanup() -> None:
    """Clean up any test-generated modules after each test."""
    yield
    for name in ["test_gen", "my_camera", "bad_module"]:
        cleanup_module(name)


class TestTemplateGenerator:
    def test_creates_module_directory(self) -> None:
        result = run_generator("test_gen", "Test generator module")
        assert result.returncode == 0
        assert (MODULES_DIR / "test_gen").is_dir()

    def test_generates_required_files(self) -> None:
        run_generator("test_gen", "Test module")
        module_dir = MODULES_DIR / "test_gen"
        assert (module_dir / "module.py").is_file()
        assert (module_dir / "capabilities.json").is_file()
        assert (module_dir / "__init__.py").is_file()

    def test_generates_test_file(self) -> None:
        run_generator("test_gen", "Test module")
        test_file = MODULES_DIR / "tests" / "test_test_gen_module.py"
        assert test_file.is_file()
        content = test_file.read_text()
        assert "TestGenModule" in content

    def test_capabilities_json_is_valid(self) -> None:
        run_generator("test_gen", "Test module")
        caps_file = MODULES_DIR / "test_gen" / "capabilities.json"
        with open(caps_file) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["capability_id"] == "tool.test_gen.example"

    def test_class_name_pascal_case(self) -> None:
        run_generator("my_camera", "Camera module")
        module_file = MODULES_DIR / "my_camera" / "module.py"
        content = module_file.read_text()
        assert "MyCameraModule" in content
        assert "my_camera" not in content.split("class ")[1].split("(")[0]

    def test_rejects_existing_module(self) -> None:
        run_generator("test_gen", "First")
        result = run_generator("test_gen", "Second")
        assert result.returncode != 0
        assert "already exists" in result.stderr or "already exists" in result.stdout

    def test_rejects_invalid_module_id(self) -> None:
        result = run_generator("123bad", "Bad name")
        assert result.returncode != 0
        assert "snake_case" in result.stderr or "snake_case" in result.stdout

    def test_custom_description_replaced(self) -> None:
        run_generator("test_gen", "My custom description")
        module_file = MODULES_DIR / "test_gen" / "module.py"
        content = module_file.read_text()
        assert "My custom description" in content
        caps_file = MODULES_DIR / "test_gen" / "capabilities.json"
        # Module manifest in module.py should have description
        assert "My custom description" in content
