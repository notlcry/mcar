"""Tests for the Mock module capabilities."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mock.module import MockModule


@pytest.fixture
def mock_module() -> MockModule:
    """Create a MockModule without starting IPC."""
    # We test the module logic directly, not IPC
    m = MockModule.__new__(MockModule)
    m._start_time = __import__("time").monotonic()
    m._cancel_events = {}
    m._stopped = False
    return m


class TestMockModuleManifest:
    def test_manifest(self, mock_module: MockModule) -> None:
        manifest = mock_module.manifest()
        assert manifest["module_id"] == "mock"
        assert "tool.mock.echo" in manifest["capabilities"]

    def test_capabilities(self, mock_module: MockModule) -> None:
        caps = mock_module.capabilities()
        assert len(caps) == 3
        cap_ids = [c["capability_id"] for c in caps]
        assert "tool.mock.echo" in cap_ids
        assert "tool.mock.timer" in cap_ids
        assert "tool.mock.status" in cap_ids


class TestMockModuleInvoke:
    @pytest.mark.asyncio
    async def test_echo(self, mock_module: MockModule) -> None:
        result = await mock_module.invoke("tool.mock.echo", {"text": "hello"}, {})
        assert result["ok"] is True
        assert result["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_status(self, mock_module: MockModule) -> None:
        result = await mock_module.invoke("tool.mock.status", {}, {})
        assert result["ok"] is True
        assert "battery" in result
        assert "temperature" in result
        assert "uptime_s" in result

    @pytest.mark.asyncio
    async def test_timer(self, mock_module: MockModule) -> None:
        result = await mock_module.invoke(
            "tool.mock.timer",
            {"duration_ms": 50},
            {"invocation_id": "test-1"},
        )
        assert result["ok"] is True
        assert result["elapsed_ms"] >= 40

    @pytest.mark.asyncio
    async def test_timer_cancel(self, mock_module: MockModule) -> None:
        async def cancel_after(ms: int) -> None:
            await asyncio.sleep(ms / 1000)
            await mock_module.cancel("test-cancel")

        task = asyncio.create_task(cancel_after(30))
        result = await mock_module.invoke(
            "tool.mock.timer",
            {"duration_ms": 5000},
            {"invocation_id": "test-cancel"},
        )
        await task
        assert result["ok"] is False  # Cancelled
        assert result["elapsed_ms"] < 500

    @pytest.mark.asyncio
    async def test_unknown_capability(self, mock_module: MockModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await mock_module.invoke("tool.mock.nonexistent", {}, {})

    @pytest.mark.asyncio
    async def test_stop(self, mock_module: MockModule) -> None:
        await mock_module.stop()
        assert mock_module._stopped is True
