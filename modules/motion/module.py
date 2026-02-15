"""Motion module — robot movement control.

Capabilities:
  - tool.motion.forward    — move forward
  - tool.motion.backward   — move backward
  - tool.motion.turn_left  — turn left
  - tool.motion.turn_right — turn right
  - tool.motion.stop       — emergency stop motors
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities

try:
    from motion.driver import MotionDriver
except ImportError:
    from driver import MotionDriver


class MotionModule(ModuleBase):
    """Motion control module using PCA9685 + DC motors."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
        mock: bool = False,
    ) -> None:
        self._driver = MotionDriver(mock=mock)
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)

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
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        speed = params.get("speed", 50)
        duration_ms = params.get("duration_ms", 1000)

        if capability_id == "tool.motion.forward":
            return await self._driver.forward(speed, duration_ms)
        if capability_id == "tool.motion.backward":
            return await self._driver.backward(speed, duration_ms)
        if capability_id == "tool.motion.turn_left":
            return await self._driver.turn_left(speed, duration_ms)
        if capability_id == "tool.motion.turn_right":
            return await self._driver.turn_right(speed, duration_ms)
        if capability_id == "tool.motion.stop":
            return await self._driver.stop()

        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        """Emergency stop: stop all motors immediately."""
        await self._driver.stop()

    async def cancel(self, invocation_id: str) -> None:
        """Cancel: trigger stop on the driver's cancel event."""
        await self._driver.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Motion module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    args = parser.parse_args()

    module = MotionModule(
        router_endpoint=args.router,
        pub_endpoint=args.pub,
        mock=args.mock,
    )
    module.run_forever()
