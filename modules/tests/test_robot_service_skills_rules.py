"""Tests for Robot Service skills and memory-backed rules."""

from __future__ import annotations

from fastapi.testclient import TestClient

from robot_service.api import create_app
from robot_service.service import create_robot_service


def test_builtin_self_check_skill_executes_sensor_steps(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    skills = client.get("/api/skills")
    result = client.post("/api/skills/skill.self_check/execute", json={"params": {}})

    assert any(skill["skill_id"] == "skill.self_check" for skill in skills.json())
    body = result.json()
    assert body["success"] is True
    assert body["steps_completed"] == 2
    assert "ultrasonic" in body["results"]
    assert "infrared" in body["results"]


def test_builtin_night_mode_sets_mute_mode(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    result = client.post("/api/skills/skill.night_mode/execute", json={"params": {}})

    body = result.json()
    assert body["success"] is True
    assert body["steps_completed"] == 2
    assert body["results"]["set_mute"] == {"ok": True, "mode": "mute"}
    assert service.state.get_mode() == "mute"


def test_skill_execute_accepts_legacy_unprefixed_skill_ids(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    result = client.post("/api/skills/self_check/execute", json={"params": {}})

    body = result.json()
    assert body["success"] is True
    assert body["skill_id"] == "skill.self_check"


def test_builtin_patrol_skill_uses_default_speed_parameter(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    result = client.post(
        "/api/skills/skill.patrol/execute",
        json={"params": {}, "confirmed": True},
    )

    body = result.json()
    assert body["success"] is True
    assert body["steps_completed"] == 3
    assert body["results"]["move_forward"]["ok"] is True


def test_dangerous_skill_requires_confirmation(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    result = client.post("/api/skills/skill.patrol/execute", json={"params": {}})

    body = result.json()
    assert body["success"] is False
    assert body["error"] == "Skill skill.patrol requires confirmation"


def test_rule_engine_sets_mode_from_rule_memory(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))
    service.memory.create(
        {
            "type": "rule",
            "content": {
                "rule_id": "kid-mode-on-obstacle",
                "when": {"state": {"key": "obstacle", "op": "==", "value": True}},
                "then": {"action": "set_mode", "mode": "kid"},
            },
            "summary": "Enter kid mode when obstacle is detected",
            "source": "user_explicit",
        }
    )
    service.state.set("obstacle", True)

    response = client.post("/api/rules/evaluate")

    assert response.json() == {
        "triggered": [{"ruleId": "kid-mode-on-obstacle", "action": "set_mode"}]
    }
    assert service.state.get_mode() == "kid"
