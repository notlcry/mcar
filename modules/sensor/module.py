"""Sensor module — ultrasonic distance + infrared obstacle detection.

Capabilities:
  - tool.sensor.ultrasonic — read HC-SR04 distance
  - tool.sensor.infrared   — read IR obstacle sensors
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities

try:
    from sensor.driver import SensorDriver
except ImportError:
    from driver import SensorDriver


class SensorModule(ModuleBase):
    """Sensor module for ultrasonic and infrared readings."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
        mock: bool = False,
    ) -> None:
        self._driver = SensorDriver(mock=mock)
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "sensor",
            "module_version": "1.0.0",
            "description": "Ultrasonic (HC-SR04) and infrared obstacle sensors",
            "capabilities": [
                "tool.sensor.ultrasonic",
                "tool.sensor.infrared",
            ],
            "permissions_required": ["gpio"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if capability_id == "tool.sensor.ultrasonic":
            return self._driver.read_ultrasonic()
        if capability_id == "tool.sensor.infrared":
            return self._driver.read_infrared()

        raise ValueError(f"Unknown capability: {capability_id}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sensor module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    args = parser.parse_args()

    module = SensorModule(
        router_endpoint=args.router,
        pub_endpoint=args.pub,
        mock=args.mock,
    )
    module.run_forever()
