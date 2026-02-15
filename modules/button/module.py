"""Button module — physical emergency stop button via GPIO.

Capabilities:
  - tool.button.status — check if button was pressed

The module also emits 'emergency_stop' events via IPC when the button
is pressed, allowing the core to trigger an immediate stop.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities

try:
    from button.driver import ButtonDriver
except ImportError:
    from driver import ButtonDriver


class ButtonModule(ModuleBase):
    """Physical emergency stop button module."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
        mock: bool = False,
    ) -> None:
        gpio_pin = int(os.environ.get("BUTTON_GPIO_PIN", "17"))
        debounce_ms = int(os.environ.get("BUTTON_DEBOUNCE_MS", "200"))
        self._driver = ButtonDriver(
            gpio_pin=gpio_pin,
            debounce_ms=debounce_ms,
            mock=mock,
        )
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)
        # Register press callback to emit IPC event
        self._driver.on_press(self._on_button_press)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "button",
            "module_version": "1.0.0",
            "description": "Physical emergency stop button (GPIO)",
            "capabilities": ["tool.button.status"],
            "permissions_required": ["gpio"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if capability_id == "tool.button.status":
            return {
                "ok": True,
                "pressed": self._driver.is_pressed(),
                "gpio_available": self._driver.gpio_available,
            }
        raise ValueError(f"Unknown capability: {capability_id}")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "gpio_available": self._driver.gpio_available,
        }

    async def stop(self) -> None:
        self._driver.cleanup()

    def _on_button_press(self) -> None:
        """Callback when physical button is pressed — emit IPC event."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    self._client.send_event("emergency_stop", {"source": "button"})
                )
            else:
                loop.run_until_complete(
                    self._client.send_event("emergency_stop", {"source": "button"})
                )
        except Exception:
            # IPC may not be connected yet during startup
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Button module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode")
    args = parser.parse_args()

    module = ButtonModule(
        router_endpoint=args.router,
        pub_endpoint=args.pub,
        mock=args.mock,
    )
    module.run_forever()
