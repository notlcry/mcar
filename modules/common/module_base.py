"""ModuleBase — abstract base class for Python hardware modules.

Each module must implement:
  - manifest()       → module metadata
  - capabilities()   → list of capability specs
  - invoke()         → execute a capability

Optional overrides:
  - health()         → health check (default: {"status": "ok"})
  - stop()           → emergency stop handler
  - cancel()         → cancel an in-flight invocation
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import signal
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .ipc_client import IpcClient

logger = logging.getLogger(__name__)


class ModuleBase(ABC):
    """Abstract base class for mcar Python modules."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
    ) -> None:
        manifest = self.manifest()
        self._module_id: str = manifest["module_id"]
        self._client = IpcClient(
            module_id=self._module_id,
            router_endpoint=router_endpoint,
            pub_endpoint=pub_endpoint,
        )
        self._client.on_message(self._handle_message)
        self._client.on_stop(self._handle_stop)
        self._stop_event = asyncio.Event()

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def client(self) -> IpcClient:
        return self._client

    # ─── Abstract interface ──────────────────────────────────

    @abstractmethod
    def manifest(self) -> dict[str, Any]:
        """Return module metadata (module_id, version, description, capabilities list)."""
        ...

    @abstractmethod
    def capabilities(self) -> list[dict[str, Any]]:
        """Return list of capability spec dicts."""
        ...

    @abstractmethod
    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a capability and return result data."""
        ...

    async def health(self) -> dict[str, Any]:
        """Return health status. Override for custom health checks."""
        return {"status": "ok"}

    async def stop(self) -> None:
        """Handle emergency stop. Override to stop hardware immediately."""
        pass

    async def cancel(self, invocation_id: str) -> None:
        """Cancel an in-flight invocation. Override for cancellable operations."""
        pass

    # ─── Lifecycle ───────────────────────────────────────────

    async def run(self) -> None:
        """Start the module and run until shutdown."""
        await self._client.start()
        logger.info("Module %s started", self._module_id)

        try:
            await self._client.run()
        except asyncio.CancelledError:
            pass
        finally:
            await self._client.stop()
            logger.info("Module %s stopped", self._module_id)

    def run_forever(self) -> None:
        """Convenience entry point: run the module in an asyncio event loop."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        loop = asyncio.new_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: self._stop_event.set())

        async def _main() -> None:
            run_task = asyncio.create_task(self.run())
            stop_task = asyncio.create_task(self._stop_event.wait())
            done, pending = await asyncio.wait(
                [run_task, stop_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        loop.run_until_complete(_main())
        loop.close()

    # ─── Message routing ─────────────────────────────────────

    async def _handle_message(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        """Route IPC messages to the appropriate method."""
        msg_type = msg.get("type")
        request_id = msg.get("id", "")

        try:
            if msg_type == "manifest":
                data = self.manifest()
                return {"type": "result", "id": request_id, "success": True, "data": data}

            if msg_type == "capabilities":
                caps = self.capabilities()
                return {
                    "type": "result",
                    "id": request_id,
                    "success": True,
                    "data": {"capabilities": caps},
                }

            if msg_type == "health":
                health_result = self.health()
                if inspect.isawaitable(health_result):
                    data = await health_result
                else:
                    data = health_result
                return {"type": "result", "id": request_id, "success": True, "data": data}

            if msg_type == "invoke":
                context = {
                    "invocation_id": request_id,
                    "idempotency_key": msg.get("idempotency_key"),
                    "timeout_ms": msg.get("timeout_ms"),
                }
                data = await self.invoke(msg["capability_id"], msg.get("params", {}), context)
                return {"type": "result", "id": request_id, "success": True, "data": data}

            if msg_type == "cancel":
                await self.cancel(msg["invocation_id"])
                return {
                    "type": "result",
                    "id": request_id,
                    "success": True,
                    "data": {"cancelled": True},
                }

            return {
                "type": "result",
                "id": request_id,
                "success": False,
                "error": {
                    "code": "E_INTERNAL",
                    "message": f"Unknown message type: {msg_type}",
                    "retryable": False,
                },
            }

        except Exception as exc:
            logger.exception("Error handling %s", msg_type)
            return {
                "type": "result",
                "id": request_id,
                "success": False,
                "error": {
                    "code": "E_INTERNAL",
                    "message": str(exc),
                    "retryable": False,
                },
            }

    async def _handle_stop(self) -> None:
        """Handle emergency stop broadcast."""
        logger.warning("EMERGENCY STOP received for module %s", self._module_id)
        try:
            await self.stop()
        except Exception:
            logger.exception("Error in stop handler")
