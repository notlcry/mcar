"""Display module — OLED screen expression and text rendering.

Capabilities:
  - tool.display.show_expression — display an expression/emotion
  - tool.display.show_text       — display text (1-4 lines)
  - tool.display.clear           — clear the screen
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities

try:
    from display.driver import DisplayDriver
except ImportError:
    from driver import DisplayDriver


class DisplayModule(ModuleBase):
    """OLED display module: expressions + text."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
        mock: bool = False,
    ) -> None:
        self._driver = DisplayDriver(mock=mock)
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)

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
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if capability_id == "tool.display.show_expression":
            expression = params.get("expression", "neutral")
            return self._driver.show_expression(expression)

        if capability_id == "tool.display.show_text":
            text = params.get("text", "")
            font_size = params.get("font_size", 12)
            return self._driver.show_text(text=text, font_size=font_size)

        if capability_id == "tool.display.clear":
            return self._driver.clear()

        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        """Emergency stop: clear display."""
        self._driver.clear()

    async def cancel(self, invocation_id: str) -> None:
        """Cancel: no long-running display ops to cancel."""
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Display module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    args = parser.parse_args()

    module = DisplayModule(
        router_endpoint=args.router,
        pub_endpoint=args.pub,
        mock=args.mock,
    )
    module.run_forever()
