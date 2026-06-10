"""Tests for Robot Service memory and audit persistence."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from robot_service.api import create_app
from robot_service.service import create_robot_service
from robot_service.storage import AuditStore


def test_memory_entries_persist_and_search(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    entry = service.memory.create(
        {
            "type": "preference",
            "content": {"name": "Wally"},
            "summary": "User likes the robot name Wally",
            "source": "user_explicit",
            "tags": ["name"],
        }
    )

    reloaded = create_robot_service(mock=True, data_dir=tmp_path)
    results = reloaded.memory.search(keywords="Wally")

    assert results[0]["id"] == entry["id"]
    assert results[0]["summary"] == "User likes the robot name Wally"


def test_memory_api_crud_and_export(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    created = client.post(
        "/api/memories",
        json={
            "type": "fact",
            "content": {"location": "desk"},
            "summary": "Robot lives on the desk",
            "source": "user_explicit",
            "tags": ["location"],
        },
    )
    memory_id = created.json()["id"]

    listed = client.get("/api/memories")
    searched = client.get("/api/memories/search?q=desk")
    exported = client.get("/api/memories/export")
    deleted = client.delete(f"/api/memories/{memory_id}")

    assert created.status_code == 200
    assert listed.json()[0]["summary"] == "Robot lives on the desk"
    assert searched.json()[0]["id"] == memory_id
    assert exported.json()["entries"][0]["id"] == memory_id
    assert deleted.json() == {"ok": True, "deleted": memory_id}
    assert client.get("/api/memories").json() == []


def test_audit_events_persist_for_invocations(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    client = TestClient(create_app(service))

    client.post(
        "/api/invoke",
        json={"capability_id": "tool.mock.echo", "params": {"text": "audit"}},
    )

    reloaded = create_robot_service(mock=True, data_dir=tmp_path)
    events = reloaded.audit_events()

    assert events
    assert events[-1]["event_type"] == "invoke.ok"
    assert events[-1]["payload"]["capability_id"] == "tool.mock.echo"


def test_audit_store_migrates_existing_schema_without_duration_ms(tmp_path) -> None:
    db_path = tmp_path / "audit.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE audit_events (
          id TEXT PRIMARY KEY,
          trace_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          payload TEXT NOT NULL,
          severity TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO audit_events (
          id, trace_id, event_type, timestamp, payload, severity
        ) VALUES (
          'old-event', 'robot-service', 'legacy', '2026-01-01T00:00:00Z', '{}', 'INFO'
        )
        """
    )
    conn.commit()
    conn.close()

    store = AuditStore(db_path)
    store.log("invoke.ok", {"capability_id": "tool.mock.echo"}, duration_ms=12)

    events = store.recent()

    assert events[0]["id"] == "old-event"
    assert events[0]["duration_ms"] is None
    assert events[-1]["event_type"] == "invoke.ok"
    assert events[-1]["duration_ms"] == 12
