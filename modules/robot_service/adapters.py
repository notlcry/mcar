"""In-process adapters over the existing mcar hardware drivers."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Protocol

from common.capability_spec import load_capabilities
from button.driver import ButtonDriver
from display.driver import DisplayDriver
from motion.driver import MotionDriver
from sensor.driver import SensorDriver
from voice.driver import VoiceDriver


class RobotModule(Protocol):
    def manifest(self) -> dict[str, Any]:
        ...

    def capabilities(self) -> list[dict[str, Any]]:
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    async def stop(self) -> None:
        ...


def _caps(module_name: str) -> list[dict[str, Any]]:
    caps_path = Path(__file__).resolve().parents[1] / module_name / "capabilities.json"
    return load_capabilities(caps_path)


class MockAdapter:
    def __init__(self) -> None:
        self._start_time = time.monotonic()
        self._cancel_events: dict[str, asyncio.Event] = {}

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "mock",
            "module_version": "1.0.0",
            "description": "Mock module with fake capabilities for testing",
            "capabilities": ["tool.mock.echo", "tool.mock.timer", "tool.mock.status"],
            "permissions_required": [],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("mock")

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.mock.echo":
            return {"ok": True, "echo": params.get("text", "")}
        if capability_id == "tool.mock.timer":
            return await self._timer(params, context)
        if capability_id == "tool.mock.status":
            uptime = time.monotonic() - self._start_time
            return {"ok": True, "battery": 0.85, "temperature": 42.5, "uptime_s": int(uptime)}
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        for event in self._cancel_events.values():
            event.set()

    async def _timer(self, params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        duration_ms = int(params.get("duration_ms", 0))
        invocation_id = str(context.get("invocation_id", ""))
        cancel_event = asyncio.Event()
        self._cancel_events[invocation_id] = cancel_event
        start = time.monotonic()
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=duration_ms / 1000)
            return {"ok": False, "elapsed_ms": int((time.monotonic() - start) * 1000)}
        except asyncio.TimeoutError:
            return {"ok": True, "elapsed_ms": int((time.monotonic() - start) * 1000)}
        finally:
            self._cancel_events.pop(invocation_id, None)


class MotionAdapter:
    def __init__(self, mock: bool = False) -> None:
        self.driver = MotionDriver(mock=mock)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "motion",
            "module_version": "1.0.0",
            "description": "Quad-wheel DC motor control via PCA9685 PWM driver",
            "capabilities": [
                "tool.motion.forward",
                "tool.motion.backward",
                "tool.motion.turn_left",
                "tool.motion.turn_right",
                "tool.motion.stop",
            ],
            "permissions_required": ["gpio", "i2c"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("motion")

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        speed = int(params.get("speed", 50))
        duration_ms = int(params.get("duration_ms", 1000))
        if capability_id == "tool.motion.forward":
            return await self.driver.forward(speed, duration_ms)
        if capability_id == "tool.motion.backward":
            return await self.driver.backward(speed, duration_ms)
        if capability_id == "tool.motion.turn_left":
            return await self.driver.turn_left(speed, duration_ms)
        if capability_id == "tool.motion.turn_right":
            return await self.driver.turn_right(speed, duration_ms)
        if capability_id == "tool.motion.stop":
            return await self.driver.stop()
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        await self.driver.stop()


class SensorAdapter:
    def __init__(self, mock: bool = False) -> None:
        self.driver = SensorDriver(mock=mock)
        self._mock_infrared: dict[str, Any] | None = None

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "sensor",
            "module_version": "1.0.0",
            "description": "Ultrasonic (HC-SR04) and infrared obstacle sensors",
            "capabilities": ["tool.sensor.ultrasonic", "tool.sensor.infrared"],
            "permissions_required": ["gpio"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("sensor")

    def set_infrared(self, left_obstacle: bool, right_obstacle: bool) -> None:
        self._mock_infrared = {
            "ok": True,
            "left_obstacle": left_obstacle,
            "right_obstacle": right_obstacle,
        }

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.sensor.ultrasonic":
            return self.driver.read_ultrasonic()
        if capability_id == "tool.sensor.infrared":
            if self._mock_infrared is not None:
                return dict(self._mock_infrared)
            return self.driver.read_infrared()
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        return None


class DisplayAdapter:
    def __init__(self, mock: bool = False) -> None:
        self.driver = DisplayDriver(mock=mock)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "display",
            "module_version": "1.0.0",
            "description": "SSD1306 OLED display: expressions and text rendering",
            "capabilities": [
                "tool.display.show_expression",
                "tool.display.show_text",
                "tool.display.clear",
            ],
            "permissions_required": ["i2c"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("display")

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.display.show_expression":
            return self.driver.show_expression(str(params.get("expression", "neutral")))
        if capability_id == "tool.display.show_text":
            return self.driver.show_text(
                text=str(params.get("text", "")),
                font_size=int(params.get("font_size", 12)),
            )
        if capability_id == "tool.display.clear":
            return self.driver.clear()
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        self.driver.clear()


class VoiceAdapter:
    def __init__(self, mock: bool = False) -> None:
        self.driver = VoiceDriver(mock=mock)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "voice",
            "module_version": "1.0.0",
            "description": "Voice I/O: ASR, TTS, wake word detection",
            "capabilities": [
                "tool.voice.recognize",
                "tool.voice.synthesize",
                "tool.voice.play_prompt",
                "tool.voice.listen_start",
                "tool.voice.listen_stop",
            ],
            "permissions_required": ["microphone", "speaker"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("voice")

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.voice.recognize":
            return await self.driver.recognize(
                language=str(params.get("language", "zh-CN")),
                timeout_s=int(params.get("timeout_s", 10)),
            )
        if capability_id == "tool.voice.synthesize":
            return await self.driver.synthesize(
                text=str(params.get("text", "")),
                voice=str(params.get("voice", "zh-CN-XiaoxiaoNeural")),
                rate=str(params.get("rate", "+0%")),
            )
        if capability_id == "tool.voice.play_prompt":
            return await self.driver.play_prompt(prompt=str(params.get("prompt", "wake")))
        if capability_id == "tool.voice.listen_start":
            return await self.driver.listen_start()
        if capability_id == "tool.voice.listen_stop":
            return await self.driver.listen_stop()
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        await self.driver.stop()


class ButtonAdapter:
    def __init__(self, mock: bool = False) -> None:
        self.driver = ButtonDriver(mock=mock)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "button",
            "module_version": "1.0.0",
            "description": "Physical emergency stop button (GPIO)",
            "capabilities": ["tool.button.status"],
            "permissions_required": ["gpio"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        return _caps("button")

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.button.status":
            return {
                "ok": True,
                "pressed": self.driver.is_pressed(),
                "gpio_available": self.driver.gpio_available,
            }
        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        return None


class RobotModules:
    def __init__(self, mock: bool = False) -> None:
        self.mock = MockAdapter()
        self.motion = MotionAdapter(mock=mock)
        self.sensor = SensorAdapter(mock=mock)
        self.display = DisplayAdapter(mock=mock)
        self.voice = VoiceAdapter(mock=mock)
        self.button = ButtonAdapter(mock=mock)

    def all(self) -> list[RobotModule]:
        return [self.mock, self.motion, self.sensor, self.display, self.voice, self.button]
