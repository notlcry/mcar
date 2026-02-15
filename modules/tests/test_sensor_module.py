"""Tests for the sensor module (mock mode)."""

from __future__ import annotations

import pytest

from sensor.driver import SensorDriver
from sensor.module import SensorModule


# ─── SensorDriver tests ──────────────────────────────────────


class TestSensorDriverUltrasonic:
    def test_read_ultrasonic_mock(self) -> None:
        driver = SensorDriver(mock=True)
        result = driver.read_ultrasonic()
        assert result["ok"] is True
        assert isinstance(result["distance_cm"], float)
        assert result["distance_cm"] > 0

    def test_read_ultrasonic_returns_valid_range(self) -> None:
        driver = SensorDriver(mock=True)
        result = driver.read_ultrasonic()
        assert 0 < result["distance_cm"] <= 300.0


class TestSensorDriverInfrared:
    def test_read_infrared_mock(self) -> None:
        driver = SensorDriver(mock=True)
        result = driver.read_infrared()
        assert result["ok"] is True
        assert isinstance(result["left_obstacle"], bool)
        assert isinstance(result["right_obstacle"], bool)

    def test_read_infrared_no_obstacle_in_mock(self) -> None:
        driver = SensorDriver(mock=True)
        result = driver.read_infrared()
        assert result["left_obstacle"] is False
        assert result["right_obstacle"] is False


class TestSensorDriverCleanup:
    def test_cleanup_mock(self) -> None:
        driver = SensorDriver(mock=True)
        driver.cleanup()  # Should not raise


# ─── SensorModule tests ──────────────────────────────────────


class TestSensorModuleManifest:
    def test_manifest(self) -> None:
        module = SensorModule(mock=True)
        m = module.manifest()
        assert m["module_id"] == "sensor"
        assert "tool.sensor.ultrasonic" in m["capabilities"]
        assert "tool.sensor.infrared" in m["capabilities"]

    def test_capabilities(self) -> None:
        module = SensorModule(mock=True)
        caps = module.capabilities()
        ids = [c["capability_id"] for c in caps]
        assert "tool.sensor.ultrasonic" in ids
        assert "tool.sensor.infrared" in ids
        for cap in caps:
            assert cap["risk_level"] == "READ_ONLY"


class TestSensorModuleInvoke:
    @pytest.fixture
    def module(self) -> SensorModule:
        return SensorModule(mock=True)

    @pytest.mark.asyncio
    async def test_invoke_ultrasonic(self, module: SensorModule) -> None:
        result = await module.invoke("tool.sensor.ultrasonic", {}, {})
        assert result["ok"] is True
        assert "distance_cm" in result

    @pytest.mark.asyncio
    async def test_invoke_infrared(self, module: SensorModule) -> None:
        result = await module.invoke("tool.sensor.infrared", {}, {})
        assert result["ok"] is True
        assert "left_obstacle" in result
        assert "right_obstacle" in result

    @pytest.mark.asyncio
    async def test_invoke_unknown(self, module: SensorModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await module.invoke("tool.sensor.nonexistent", {}, {})
