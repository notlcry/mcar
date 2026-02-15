"""IPC Client — ZeroMQ DEALER + SUB for Python modules.

Connects to the Node.js ModuleBridge:
- DEALER socket for request/response (register, invoke results, heartbeat)
- SUB socket for emergency stop broadcast
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class IpcClient:
    """ZeroMQ IPC client for a Python module process."""

    def __init__(
        self,
        module_id: str,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
    ) -> None:
        self._module_id = module_id
        self._router_endpoint = router_endpoint
        self._pub_endpoint = pub_endpoint
        self._ctx: zmq.asyncio.Context | None = None
        self._dealer: zmq.asyncio.Socket | None = None
        self._sub: zmq.asyncio.Socket | None = None
        self._running = False
        self._message_handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]] | None = None
        self._stop_handler: Callable[[], Awaitable[None]] | None = None

    @property
    def module_id(self) -> str:
        return self._module_id

    def on_message(
        self, handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]
    ) -> None:
        """Set handler for incoming messages (invoke, manifest, capabilities, health, cancel)."""
        self._message_handler = handler

    def on_stop(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set handler for emergency stop broadcast."""
        self._stop_handler = handler

    async def start(self) -> None:
        """Connect to the bridge and start receive loops."""
        self._ctx = zmq.asyncio.Context()

        # DEALER socket for main communication
        self._dealer = self._ctx.socket(zmq.DEALER)
        self._dealer.setsockopt(zmq.IDENTITY, self._module_id.encode("utf-8"))
        self._dealer.connect(self._router_endpoint)

        # SUB socket for emergency stop
        self._sub = self._ctx.socket(zmq.SUB)
        self._sub.connect(self._pub_endpoint)
        self._sub.subscribe(b"stop")

        self._running = True

        # Register with the bridge
        await self._send({"type": "register", "module_id": self._module_id})

        logger.info("IPC client started for module %s", self._module_id)

    async def run(self) -> None:
        """Run receive loops. Call after start()."""
        await asyncio.gather(
            self._dealer_loop(),
            self._sub_loop(),
        )

    async def stop(self) -> None:
        """Disconnect and clean up."""
        self._running = False

        if self._dealer:
            self._dealer.close(linger=0)
            self._dealer = None
        if self._sub:
            self._sub.close(linger=0)
            self._sub = None
        if self._ctx:
            self._ctx.term()
            self._ctx = None

        logger.info("IPC client stopped for module %s", self._module_id)

    async def send_result(
        self,
        request_id: str,
        success: bool,
        data: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Send a result back to the bridge."""
        if success:
            msg = {"type": "result", "id": request_id, "success": True, "data": data or {}}
        else:
            msg = {"type": "result", "id": request_id, "success": False, "error": error or {}}
        await self._send(msg)

    async def send_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send an unsolicited event to the bridge."""
        import time

        msg = {
            "type": "event",
            "source": self._module_id,
            "event_type": event_type,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        await self._send(msg)

    # ─── Internal ────────────────────────────────────────────

    async def _send(self, msg: dict[str, Any]) -> None:
        if not self._dealer:
            raise RuntimeError("IPC client not started")
        payload = json.dumps(msg).encode("utf-8")
        await self._dealer.send_multipart([b"", payload])

    async def _dealer_loop(self) -> None:
        """Receive messages from the bridge via DEALER socket."""
        if not self._dealer:
            return

        while self._running:
            try:
                frames = await self._dealer.recv_multipart()
                # DEALER receives [empty_frame, payload]
                payload = frames[-1]
                msg = json.loads(payload.decode("utf-8"))
                await self._handle_dealer_message(msg)
            except zmq.ZMQError:
                if self._running:
                    logger.exception("DEALER receive error")
                break
            except Exception:
                logger.exception("Error handling dealer message")

    async def _sub_loop(self) -> None:
        """Receive emergency stop broadcasts via SUB socket."""
        if not self._sub:
            return

        while self._running:
            try:
                frames = await self._sub.recv_multipart()
                # SUB receives [topic, payload]
                if len(frames) >= 2:
                    msg = json.loads(frames[1].decode("utf-8"))
                    if msg.get("type") == "stop" and self._stop_handler:
                        await self._stop_handler()
            except zmq.ZMQError:
                if self._running:
                    logger.exception("SUB receive error")
                break
            except Exception:
                logger.exception("Error handling stop broadcast")

    async def _handle_dealer_message(self, msg: dict[str, Any]) -> None:
        """Route incoming messages to the appropriate handler."""
        msg_type = msg.get("type")

        if msg_type == "heartbeat_ping":
            await self._send({
                "type": "heartbeat_pong",
                "id": msg["id"],
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
            })
            return

        if self._message_handler:
            try:
                response = await self._message_handler(msg)
                if response:
                    await self._send(response)
            except Exception as exc:
                logger.exception("Message handler error for %s", msg_type)
                if "id" in msg:
                    await self.send_result(
                        msg["id"],
                        success=False,
                        error={
                            "code": "E_INTERNAL",
                            "message": str(exc),
                            "retryable": False,
                        },
                    )
