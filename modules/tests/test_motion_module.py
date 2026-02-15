"""Tests for the Motion module capabilities (mock mode)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motion.driver import MotionDriver
from motion.module import MotionModule


@pytest.fixture
def motion_driver() -> MotionDriver:
    """Create a MotionDriver in mock mode."""
    return MotionDriver(mock=True)


@pytest.fixture
def motion_module() -> MotionModule:
    """Create a MotionModule without starting IPC."""
    m = MotionModule.__new__(MotionModule)
    m._driver = MotionDriver(mock=True)
    return m


class TestMotionModuleManifest:
    def test_manifest(self, motion_module: MotionModule) -> None:
        manifest = motion_module.manifest()
        assert manifest["module_id"] == "motion"
        assert "tool.motion.forward" in manifest["capabilities"]
        assert "tool.motion.backward" in manifest["capabilities"]
        assert "tool.motion.turn_left" in manifest["capabilities"]
        assert "tool.motion.turn_right" in manifest["capabilities"]
        assert "tool.motion.stop" in manifest["capabilities"]

    def test_capabilities(self, motion_module: MotionModule) -> None:
        caps = motion_module.capabilities()
        assert len(caps) == 5
        cap_ids = [c["capability_id"] for c in caps]
        assert "tool.motion.forward" in cap_ids
        assert "tool.motion.backward" in cap_ids
        assert "tool.motion.turn_left" in cap_ids
        assert "tool.motion.turn_right" in cap_ids
        assert "tool.motion.stop" in cap_ids


class TestMotionDriverMovement:
    @pytest.mark.asyncio
    async def test_forward_mock(self, motion_driver: MotionDriver) -> None:
        result = await motion_driver.forward(speed=30, duration_ms=100)
        assert result["ok"] is True
        assert "actual_duration_ms" in result

    @pytest.mark.asyncio
    async def test_backward_mock(self, motion_driver: MotionDriver) -> None:
        result = await motion_driver.backward(speed=30, duration_ms=100)
        assert result["ok"] is True
        assert "actual_duration_ms" in result

    @pytest.mark.asyncio
    async def test_turn_left_mock(self, motion_driver: MotionDriver) -> None:
        result = await motion_driver.turn_left(speed=30, duration_ms=100)
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_turn_right_mock(self, motion_driver: MotionDriver) -> None:
        result = await motion_driver.turn_right(speed=30, duration_ms=100)
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_speed_clamped(self, motion_driver: MotionDriver) -> None:
        """Speed values beyond 0-100 should be clamped."""
        result = await motion_driver.forward(speed=200, duration_ms=100)
        assert result["ok"] is True


class TestMotionModuleInvoke:
    @pytest.mark.asyncio
    async def test_invoke_forward(self, motion_module: MotionModule) -> None:
        result = await motion_module.invoke(
            "tool.motion.forward", {"speed": 30, "duration_ms": 100}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_backward(self, motion_module: MotionModule) -> None:
        result = await motion_module.invoke(
            "tool.motion.backward", {"speed": 30, "duration_ms": 100}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_turn_left(self, motion_module: MotionModule) -> None:
        result = await motion_module.invoke(
            "tool.motion.turn_left", {"speed": 30, "duration_ms": 100}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_turn_right(self, motion_module: MotionModule) -> None:
        result = await motion_module.invoke(
            "tool.motion.turn_right", {"speed": 30, "duration_ms": 100}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_stop(self, motion_module: MotionModule) -> None:
        result = await motion_module.invoke("tool.motion.stop", {}, {})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_unknown(self, motion_module: MotionModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await motion_module.invoke("tool.motion.nonexistent", {}, {})


class TestMotionDriverEmergencyStop:
    @pytest.mark.asyncio
    async def test_stop(self, motion_driver: MotionDriver) -> None:
        result = await motion_driver.stop()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_cleanup(self, motion_driver: MotionDriver) -> None:
        motion_driver.cleanup()
        # Should not raise


class TestMotionCapabilitiesSpec:
    def test_forward_has_obstacle_predicate(self, motion_module: MotionModule) -> None:
        caps = motion_module.capabilities()
        fwd = next(c for c in caps if c["capability_id"] == "tool.motion.forward")
        preds = fwd["required_state_predicates"]
        obstacle_pred = next((p for p in preds if p["key"] == "obstacle"), None)
        assert obstacle_pred is not None
        assert obstacle_pred["op"] == "=="
        assert obstacle_pred["value"] is False
        assert obstacle_pred["on_fail"] == "DENY"

    def test_all_movement_have_mutex_group(self, motion_module: MotionModule) -> None:
        caps = motion_module.capabilities()
        movement_caps = [c for c in caps if c["capability_id"] != "tool.motion.stop"]
        for cap in movement_caps:
            assert cap["constraints"]["concurrency"]["mutex_group"] == "motion"
            assert cap["constraints"]["concurrency"]["max_in_flight"] == 1

    def test_all_movement_dedup_only(self, motion_module: MotionModule) -> None:
        caps = motion_module.capabilities()
        movement_caps = [c for c in caps if c["capability_id"] != "tool.motion.stop"]
        for cap in movement_caps:
            assert cap["idempotency"]["mode"] == "DEDUP_ONLY"

    def test_stop_is_read_only(self, motion_module: MotionModule) -> None:
        caps = motion_module.capabilities()
        stop = next(c for c in caps if c["capability_id"] == "tool.motion.stop")
        assert stop["risk_level"] == "READ_ONLY"
