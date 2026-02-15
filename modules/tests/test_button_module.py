"""Tests for the button module (mock mode)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from button.driver import ButtonDriver
from button.module import ButtonModule


# ─── ButtonDriver tests ──────────────────────────────────────


class TestButtonDriverInit:
    def test_mock_mode_no_gpio(self) -> None:
        driver = ButtonDriver(mock=True)
        assert driver.gpio_available is False
        assert driver._mock is True

    def test_default_gpio_pin(self) -> None:
        driver = ButtonDriver(mock=True)
        assert driver.gpio_pin == 17

    def test_custom_gpio_pin(self) -> None:
        driver = ButtonDriver(gpio_pin=27, mock=True)
        assert driver.gpio_pin == 27

    def test_custom_debounce(self) -> None:
        driver = ButtonDriver(debounce_ms=500, mock=True)
        assert driver.debounce_ms == 500


class TestButtonDriverPress:
    def test_not_pressed_initially(self) -> None:
        driver = ButtonDriver(mock=True)
        assert driver.is_pressed() is False

    def test_simulate_press(self) -> None:
        driver = ButtonDriver(mock=True)
        driver.simulate_press()
        assert driver.is_pressed() is True

    def test_is_pressed_resets_after_read(self) -> None:
        """is_pressed() is edge-triggered: returns True once then resets."""
        driver = ButtonDriver(mock=True)
        driver.simulate_press()
        assert driver.is_pressed() is True
        assert driver.is_pressed() is False

    def test_callback_on_press(self) -> None:
        driver = ButtonDriver(mock=True)
        called = []
        driver.on_press(lambda: called.append(True))
        driver.simulate_press()
        assert len(called) == 1

    def test_multiple_presses_trigger_callback_each_time(self) -> None:
        driver = ButtonDriver(mock=True)
        called = []
        driver.on_press(lambda: called.append(True))
        driver.simulate_press()
        driver.simulate_press()
        assert len(called) == 2


class TestButtonDriverCleanup:
    def test_cleanup_mock(self) -> None:
        driver = ButtonDriver(mock=True)
        driver.cleanup()  # Should not raise


# ─── ButtonModule tests ──────────────────────────────────────


class TestButtonModuleManifest:
    def test_manifest(self) -> None:
        module = ButtonModule(mock=True)
        m = module.manifest()
        assert m["module_id"] == "button"
        assert "tool.button.status" in m["capabilities"]
        assert "gpio" in m["permissions_required"]

    def test_capabilities(self) -> None:
        module = ButtonModule(mock=True)
        caps = module.capabilities()
        assert len(caps) == 1
        assert caps[0]["capability_id"] == "tool.button.status"
        assert caps[0]["risk_level"] == "READ_ONLY"


class TestButtonModuleInvoke:
    @pytest.fixture
    def module(self) -> ButtonModule:
        return ButtonModule(mock=True)

    @pytest.mark.asyncio
    async def test_invoke_status_not_pressed(self, module: ButtonModule) -> None:
        result = await module.invoke("tool.button.status", {}, {})
        assert result["ok"] is True
        assert result["pressed"] is False
        assert result["gpio_available"] is False  # mock mode

    @pytest.mark.asyncio
    async def test_invoke_status_after_press(self, module: ButtonModule) -> None:
        module._driver.simulate_press()
        result = await module.invoke("tool.button.status", {}, {})
        assert result["ok"] is True
        assert result["pressed"] is True

    @pytest.mark.asyncio
    async def test_invoke_unknown(self, module: ButtonModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await module.invoke("tool.button.nonexistent", {}, {})


class TestButtonModuleHealth:
    def test_health_mock(self) -> None:
        module = ButtonModule(mock=True)
        h = module.health()
        assert h["status"] == "ok"
        assert h["gpio_available"] is False


class TestButtonModuleStop:
    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        module = ButtonModule(mock=True)
        await module.stop()  # Should not raise


class TestButtonCapabilitiesSpec:
    """Verify capabilities.json matches Spec.md requirements."""

    @pytest.fixture
    def caps(self) -> list[dict]:
        caps_file = Path(__file__).resolve().parent.parent / "button" / "capabilities.json"
        with open(caps_file) as f:
            return json.load(f)

    def test_status_is_read_only(self, caps: list[dict]) -> None:
        status_cap = next(c for c in caps if c["capability_id"] == "tool.button.status")
        assert status_cap["risk_level"] == "READ_ONLY"

    def test_status_timeout(self, caps: list[dict]) -> None:
        status_cap = next(c for c in caps if c["capability_id"] == "tool.button.status")
        assert status_cap["constraints"]["timeout_ms"] == 1000

    def test_status_no_confirm_required(self, caps: list[dict]) -> None:
        status_cap = next(c for c in caps if c["capability_id"] == "tool.button.status")
        assert status_cap["permissions"]["confirm_required"] is False
