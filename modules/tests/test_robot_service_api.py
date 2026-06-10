"""Tests for the Python Robot Service HTTP API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from robot_service.api import create_app
from robot_service.service import create_robot_service


def test_api_invoke_uses_safety_router() -> None:
    service = create_robot_service(mock=True)
    service.state.set("obstacle", True)
    client = TestClient(create_app(service))

    response = client.post(
        "/api/invoke",
        json={
            "capability_id": "tool.motion.forward",
            "params": {"speed": 30, "duration_ms": 100},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E_STATE_OBSTACLE"


def test_api_invoke_accepts_legacy_input_field() -> None:
    service = create_robot_service(mock=True)
    client = TestClient(create_app(service))

    response = client.post(
        "/api/invoke",
        json={"capability_id": "tool.mock.echo", "input": {"text": "hello"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["echo"] == "hello"


def test_api_chat_handles_motion_command_locally_without_llm(tmp_path: Path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    async def fail_chat(text: str) -> str:
        raise AssertionError(f"LLM should not be called for local motion command: {text}")

    service.agent.chat = fail_chat

    response = client.post(
        "/api/chat",
        json={"text": "向前走100毫秒，速度10，然后停止。"},
    )

    assert response.status_code == 200
    assert response.json() == {"response": "执行完毕。"}
    motion_events = [
        event for event in service.audit_events() if event["payload"].get("capability_id")
    ]
    assert motion_events[-1]["payload"]["capability_id"] == "tool.motion.forward"
    assert motion_events[-1]["payload"]["duration_ms"] >= 100


def test_api_chat_handles_routine_command_locally_without_llm(tmp_path: Path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    async def fail_chat(text: str) -> str:
        raise AssertionError(f"LLM should not be called for local routine command: {text}")

    service.agent.chat = fail_chat

    response = client.post("/api/chat", json={"text": "转个圈"})

    assert response.status_code == 200
    assert response.json() == {"response": "执行完毕。"}
    motion_events = [
        event for event in service.audit_events() if event["payload"].get("capability_id")
    ]
    assert len(motion_events) >= 1
    assert all(
        event["payload"]["capability_id"] == "tool.motion.turn_right"
        for event in motion_events[-2:]
    )


def test_api_stop_sets_safety_lock() -> None:
    service = create_robot_service(mock=True)
    client = TestClient(create_app(service))

    response = client.post("/api/stop")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert service.state.estop_locked is True


def test_api_voice_run_once_triggers_voice_session(tmp_path: Path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))
    calls: list[tuple[str, dict]] = []

    async def fake_voice_invoke(capability_id: str, params: dict, context: dict) -> dict:
        calls.append((capability_id, dict(params)))
        if capability_id == "tool.voice.listen_stop":
            return {"ok": True}
        if capability_id == "tool.voice.play_prompt":
            return {"ok": True, "prompt": params.get("prompt"), "duration_ms": 5}
        if capability_id == "tool.voice.recognize":
            return {"ok": True, "text": "看一下状态"}
        if capability_id == "tool.voice.synthesize":
            return {"ok": True, "duration_ms": 5}
        if capability_id == "tool.voice.listen_start":
            return {"ok": True, "listening": True}
        raise AssertionError(f"unexpected voice capability: {capability_id}")

    async def fake_chat(text: str) -> str:
        return "状态正常"

    service.modules.voice.invoke = fake_voice_invoke
    service.chat = fake_chat  # type: ignore[method-assign]

    response = client.post("/api/voice/run_once", json={"source": "e2e_probe"})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "text": "看一下状态", "response": "状态正常"}
    assert calls[0] == ("tool.voice.listen_stop", {})
    assert calls[-1] == ("tool.voice.listen_start", {})


def test_api_startup_starts_voice_listener(tmp_path: Path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls: list[tuple[str, dict]] = []

    async def fake_voice_invoke(capability_id: str, params: dict, context: dict) -> dict:
        calls.append((capability_id, dict(params)))
        if capability_id == "tool.voice.listen_start":
            return {"ok": True, "listening": True}
        raise AssertionError(f"unexpected voice capability: {capability_id}")

    service.modules.voice.invoke = fake_voice_invoke

    with TestClient(create_app(service)):
        pass

    assert calls == [("tool.voice.listen_start", {})]
    events = service.audit_events(limit=5)
    assert any(event["event_type"] == "voice.listen.started" for event in events)


def test_api_provides_web_console_compatibility_endpoints() -> None:
    service = create_robot_service(mock=True)
    client = TestClient(create_app(service))

    memories = client.get("/api/memories")
    memory_search = client.get("/api/memories/search?q=test")
    memory_export = client.get("/api/memories/export")
    module_enable = client.post("/api/modules/motion/enable")
    module_disable = client.post("/api/modules/motion/disable")
    watchdog = client.get("/api/watchdog")
    replay = client.get("/api/sessions/test-session/replay")

    assert memories.status_code == 200
    assert memories.json() == []
    assert memory_search.status_code == 200
    assert memory_search.json() == []
    assert memory_export.status_code == 200
    assert memory_export.json()["entries"] == []
    assert module_enable.json() == {"ok": True, "moduleId": "motion", "enabled": True}
    assert module_disable.json() == {"ok": True, "moduleId": "motion", "enabled": False}
    assert watchdog.json()[0]["permanentlyFailed"] is False
    assert replay.json() == {"sessionId": "test-session", "events": []}


def test_web_console_uses_robot_service_status_fields() -> None:
    service = create_robot_service(mock=True)
    client = TestClient(create_app(service))

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert "s.battery ?? s.batteryLevel" in html
    assert "s.estopLocked ?? s.safetyLock" in html
