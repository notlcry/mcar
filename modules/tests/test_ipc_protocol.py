"""Tests for IPC protocol message serialization and module base."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.capability_spec import build_capability, load_capabilities
from common.types import ModuleManifest, CapabilitySpec, IpcError


class TestCapabilitySpec:
    def test_build_capability_defaults(self) -> None:
        cap = build_capability(
            capability_id="tool.test.echo",
            name="Echo",
            description="Echo test",
        )
        assert cap["capability_id"] == "tool.test.echo"
        assert cap["risk_level"] == "READ_ONLY"
        assert cap["type"] == "tool"
        assert cap["constraints"]["timeout_ms"] == 5000

    def test_build_capability_custom(self) -> None:
        cap = build_capability(
            capability_id="tool.test.danger",
            name="Danger",
            description="Dangerous action",
            risk_level="DANGEROUS",
            constraints={"timeout_ms": 10000, "cooldown_ms": 1000},
        )
        assert cap["risk_level"] == "DANGEROUS"
        assert cap["constraints"]["cooldown_ms"] == 1000

    def test_load_capabilities_from_json(self) -> None:
        caps_file = Path(__file__).resolve().parent.parent / "mock" / "capabilities.json"
        caps = load_capabilities(caps_file)
        assert len(caps) == 3
        assert caps[0]["capability_id"] == "tool.mock.echo"
        assert caps[1]["capability_id"] == "tool.mock.timer"
        assert caps[2]["capability_id"] == "tool.mock.status"


class TestTypes:
    def test_module_manifest_frozen(self) -> None:
        m = ModuleManifest(
            module_id="test",
            module_version="1.0.0",
            description="Test module",
            capabilities=["cap1"],
        )
        assert m.module_id == "test"
        with pytest.raises(AttributeError):
            m.module_id = "changed"  # type: ignore[misc]

    def test_ipc_error_frozen(self) -> None:
        err = IpcError(code="E_INTERNAL", message="Something went wrong")
        assert err.code == "E_INTERNAL"
        assert err.retryable is False

    def test_capability_spec_defaults(self) -> None:
        spec = CapabilitySpec(
            capability_id="tool.test",
            name="Test",
            type="tool",
            version="1.0.0",
            description="Test capability",
            risk_level="READ_ONLY",
        )
        assert spec.inputs_schema == {}
        assert spec.required_state_predicates == []
