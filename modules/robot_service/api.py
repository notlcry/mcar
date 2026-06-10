"""FastAPI app for the Python Robot Service."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect

from .models import ChatRequest, InvokeRequest, ModeRequest
from .service import RobotService, create_robot_service


def create_app(service: RobotService | None = None) -> FastAPI:
    robot = service or create_robot_service(mock=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await _start_voice_listener(robot)
        yield

    app = FastAPI(title="mcar Robot Service", lifespan=lifespan)

    @app.get("/api/status")
    def status() -> dict:
        return robot.status()

    @app.get("/api/capabilities")
    def capabilities() -> list[dict]:
        return [cap.model_dump() for cap in robot.registry.summaries()]

    @app.get("/api/modules")
    def modules() -> list[dict]:
        return [module.model_dump() for module in robot.registry.modules()]

    @app.post("/api/modules/{module_id}/enable")
    def enable_module(module_id: str) -> dict:
        return {"ok": True, "moduleId": module_id, "enabled": True}

    @app.post("/api/modules/{module_id}/disable")
    def disable_module(module_id: str) -> dict:
        return {"ok": True, "moduleId": module_id, "enabled": False}

    @app.post("/api/invoke")
    async def invoke(request: InvokeRequest) -> dict:
        result = await robot.invoke(request.capability_id, request.invocation_params())
        return result.model_dump(exclude_none=True)

    @app.post("/api/stop")
    async def stop() -> dict:
        return await robot.trigger_stop("web")

    @app.post("/api/mode")
    def mode(request: ModeRequest) -> dict:
        return robot.set_mode(request.mode)

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict:
        return {"response": await robot.chat(request.text)}

    @app.post("/api/voice/run_once")
    async def voice_run_once(data: dict | None = None) -> dict:
        payload = data or {}
        source = str(payload.get("source") or "api")
        return await robot.voice_session.run_once(source=source)

    @app.get("/api/memories")
    def memories() -> list[dict]:
        return robot.memory.list_summaries()

    @app.post("/api/memories")
    def memory_create(memory: dict) -> dict:
        return robot.memory.create(memory)

    @app.get("/api/memories/search")
    def memory_search(q: str) -> list[dict]:
        return robot.memory.search(keywords=q)

    @app.get("/api/memories/export")
    def memory_export() -> dict:
        return robot.memory.export()

    @app.post("/api/memories/import")
    def memory_import(data: dict) -> dict:
        return robot.memory.import_entries(data)

    @app.post("/api/memories/clear")
    def memory_clear(data: dict) -> dict:
        memory_type = data.get("type")
        if not memory_type:
            return {"ok": False, "cleared": 0}
        return {"ok": True, "cleared": robot.memory.clear_by_type(memory_type)}

    @app.delete("/api/memories/{memory_id}")
    def memory_delete(memory_id: str) -> dict:
        robot.memory.delete(memory_id)
        return {"ok": True, "deleted": memory_id}

    @app.get("/api/health")
    def health() -> dict:
        return robot.health()

    @app.get("/api/audit")
    def audit() -> list[dict]:
        return robot.audit_events()

    @app.get("/api/audit/export")
    def audit_export() -> dict:
        entries = robot.audit_events(limit=10000)
        return {"version": "1.0.0", "count": len(entries), "entries": entries}

    @app.get("/api/metrics")
    def metrics() -> list[dict]:
        return []

    @app.get("/api/watchdog")
    def watchdog() -> list[dict]:
        return [
            {
                "moduleId": module.module_id,
                "status": "in_process",
                "restartCount": 0,
                "permanentlyFailed": False,
            }
            for module in robot.registry.modules()
        ]

    @app.get("/api/skills")
    def skills() -> list[dict]:
        return robot.skills.list()

    @app.post("/api/skills/{skill_id}/execute")
    async def skill_execute(skill_id: str, data: dict | None = None) -> dict:
        payload = data or {}
        params = payload.get("params") or {}
        role = str(payload.get("role") or "user")
        confirmed = bool(payload.get("confirmed") or False)
        return await robot.skills.execute(skill_id, params, role=role, confirmed=confirmed)

    @app.get("/api/sessions")
    def sessions() -> list[dict]:
        return []

    @app.get("/api/sessions/{session_id}/replay")
    def session_replay(session_id: str) -> dict:
        return {"sessionId": session_id, "events": []}

    @app.get("/api/rules/status")
    def rules_status() -> dict:
        return {"available": True}

    @app.post("/api/rules/evaluate")
    async def rules_evaluate() -> dict:
        return {"triggered": await robot.rules.evaluate()}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket) -> None:
        await ws.accept()
        await ws.send_json({"type": "state_change", "data": robot.status()})
        try:
            while True:
                message = await ws.receive_json()
                message_type = message.get("type")
                data = message.get("data") or {}
                if message_type == "chat":
                    response = await robot.chat(data.get("text", ""))
                    await ws.send_json({"type": "chat", "data": {"response": response}})
                elif message_type == "stop":
                    await robot.trigger_stop("websocket")
                    await ws.send_json({"type": "state_change", "data": robot.status()})
                elif message_type == "mode":
                    robot.set_mode(data["mode"])
                    await ws.send_json({"type": "state_change", "data": robot.status()})
        except WebSocketDisconnect:
            return

    public_dir = Path(__file__).resolve().parents[2] / "core" / "src" / "web" / "public"
    if public_dir.exists():
        app.mount("/static", StaticFiles(directory=public_dir), name="static")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(public_dir / "index.html")

    return app


async def _start_voice_listener(robot: RobotService) -> None:
    robot.audit("voice.session.configured", robot.voice_session.config_payload())
    if not _env_bool(os.environ.get("VOICE_AUTO_LISTEN_ENABLED", "true")):
        robot.audit("voice.listen.skipped", {"reason": "disabled"})
        return
    result = await robot.invoke("tool.voice.listen_start", {})
    data = result.data or {}
    if result.success and data.get("ok", False):
        await robot.set_session_state("IDLE")
        robot.audit(
            "voice.listen.started",
            {"wake_word": data.get("wake_word"), "listening": data.get("listening")},
        )
        return
    error = result.error.message if result.error else data.get("error", "unknown")
    robot.audit("voice.listen.failed", {"error": error})


def _env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
