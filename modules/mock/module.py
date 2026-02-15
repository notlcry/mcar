"""Mock module — 3 fake capabilities for IPC testing.

Capabilities:
  - tool.mock.echo    — echo back input text
  - tool.mock.timer   — wait for duration_ms, cancellable
  - tool.mock.status  — return fake system status
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities


class MockModule(ModuleBase):
    """Mock hardware module for development and CI testing."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
    ) -> None:
        self._start_time = time.monotonic()
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._stopped = False
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "mock",
            "module_version": "1.0.0",
            "description": "Mock module with fake capabilities for testing",
            "capabilities": [
                "tool.mock.echo",
                "tool.mock.timer",
                "tool.mock.status",
            ],
            "permissions_required": [],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if capability_id == "tool.mock.echo":
            return await self._echo(params)
        if capability_id == "tool.mock.timer":
            return await self._timer(params, context)
        if capability_id == "tool.mock.status":
            return await self._status()

        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        """Emergency stop: cancel all pending timers."""
        self._stopped = True
        for event in self._cancel_events.values():
            event.set()

    async def cancel(self, invocation_id: str) -> None:
        event = self._cancel_events.get(invocation_id)
        if event:
            event.set()

    # ─── Capability implementations ──────────────────────────

    async def _echo(self, params: dict[str, Any]) -> dict[str, Any]:
        text = params.get("text", "")
        return {"ok": True, "echo": text}

    async def _timer(self, params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        duration_ms = params.get("duration_ms", 0)
        invocation_id = context.get("invocation_id", "")

        cancel_event = asyncio.Event()
        self._cancel_events[invocation_id] = cancel_event

        start = time.monotonic()
        try:
            await asyncio.wait_for(
                cancel_event.wait(),
                timeout=duration_ms / 1000.0,
            )
            # If we get here, it was cancelled
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {"ok": False, "elapsed_ms": elapsed_ms}
        except asyncio.TimeoutError:
            # Normal completion
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {"ok": True, "elapsed_ms": elapsed_ms}
        finally:
            self._cancel_events.pop(invocation_id, None)

    async def _status(self) -> dict[str, Any]:
        uptime = time.monotonic() - self._start_time
        return {
            "ok": True,
            "battery": 0.85,
            "temperature": 42.5,
            "uptime_s": int(uptime),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    args = parser.parse_args()

    module = MockModule(router_endpoint=args.router, pub_endpoint=args.pub)
    module.run_forever()
