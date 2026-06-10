"""SQLite-backed memory and audit storage for Robot Service."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from threading import RLock
from typing import Any


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
              id TEXT PRIMARY KEY,
              type TEXT NOT NULL,
              content TEXT NOT NULL,
              summary TEXT NOT NULL,
              source TEXT NOT NULL,
              confidence REAL NOT NULL,
              privacy_level TEXT NOT NULL,
              tags TEXT NOT NULL,
              links TEXT NOT NULL,
              ttl REAL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def create(self, input_data: dict[str, Any]) -> dict[str, Any]:
        timestamp = now_iso()
        entry = {
            "id": input_data.get("id") or str(uuid.uuid4()),
            "type": input_data["type"],
            "content": input_data.get("content") or {},
            "summary": input_data["summary"],
            "source": input_data.get("source") or "user_explicit",
            "confidence": float(input_data.get("confidence", 1.0)),
            "privacy_level": input_data.get("privacy_level") or "normal",
            "tags": list(input_data.get("tags") or []),
            "links": dict(input_data.get("links") or {}),
            "ttl": input_data.get("ttl"),
            "created_at": input_data.get("created_at") or timestamp,
            "updated_at": input_data.get("updated_at") or timestamp,
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO memories (
                  id, type, content, summary, source, confidence, privacy_level,
                  tags, links, ttl, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["id"],
                    entry["type"],
                    json.dumps(entry["content"], ensure_ascii=False),
                    entry["summary"],
                    entry["source"],
                    entry["confidence"],
                    entry["privacy_level"],
                    json.dumps(entry["tags"], ensure_ascii=False),
                    json.dumps(entry["links"], ensure_ascii=False),
                    entry["ttl"],
                    entry["created_at"],
                    entry["updated_at"],
                ),
            )
            self._conn.commit()
        return entry

    def search(
        self,
        *,
        keywords: str | None = None,
        types: list[str] | None = None,
        include_private: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            entries = [
                self._row_to_entry(row)
                for row in self._conn.execute("SELECT * FROM memories")
            ]
        if types:
            allowed = set(types)
            entries = [entry for entry in entries if entry["type"] in allowed]
        if not include_private:
            entries = [entry for entry in entries if entry["privacy_level"] != "private"]
        if keywords:
            needles = [word.lower() for word in keywords.split() if word.strip()]
            entries = [entry for entry in entries if self._matches_keywords(entry, needles)]
        entries.sort(key=lambda entry: entry["updated_at"], reverse=True)
        return entries[:limit]

    def list_summaries(self) -> list[dict[str, Any]]:
        return [
            {"id": entry["id"], "type": entry["type"], "summary": entry["summary"]}
            for entry in self.search()
        ]

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.commit()
        return cursor.rowcount > 0

    def clear_by_type(self, memory_type: str) -> int:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM memories WHERE type = ?", (memory_type,))
            self._conn.commit()
        return cursor.rowcount

    def export(self) -> dict[str, Any]:
        return {"version": "1.0.0", "entries": self.search(include_private=True, limit=10000)}

    def import_entries(self, data: dict[str, Any]) -> dict[str, Any]:
        imported = 0
        errors: list[str] = []
        with self._lock:
            for entry in data.get("entries", []):
                try:
                    self.create(entry)
                    imported += 1
                except Exception as exc:
                    errors.append(str(exc))
        return {"imported": imported, "skipped": 0, "errors": errors}

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _row_to_entry(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["type"],
            "content": json.loads(row["content"]),
            "summary": row["summary"],
            "source": row["source"],
            "confidence": row["confidence"],
            "privacy_level": row["privacy_level"],
            "tags": json.loads(row["tags"]),
            "links": json.loads(row["links"]),
            "ttl": row["ttl"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _matches_keywords(self, entry: dict[str, Any], needles: list[str]) -> bool:
        haystack = " ".join(
            [
                entry["summary"],
                " ".join(entry["tags"]),
                json.dumps(entry["content"], ensure_ascii=False),
            ]
        ).lower()
        return all(needle in haystack for needle in needles)


class AuditStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY,
              trace_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              timestamp TEXT NOT NULL,
              payload TEXT NOT NULL,
              severity TEXT NOT NULL,
              duration_ms INTEGER
            )
            """
        )
        self._ensure_column("audit_events", "duration_ms", "INTEGER")
        self._conn.commit()

    def log(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        trace_id: str = "robot-service",
        severity: str = "INFO",
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "event_type": event_type,
            "timestamp": now_iso(),
            "payload": payload,
            "severity": severity,
            "duration_ms": duration_ms,
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO audit_events (
                  id, trace_id, event_type, timestamp, payload, severity, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["trace_id"],
                    event["event_type"],
                    event["timestamp"],
                    json.dumps(event["payload"], ensure_ascii=False),
                    event["severity"],
                    event["duration_ms"],
                ),
            )
            self._conn.commit()
        return event

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_events ORDER BY timestamp DESC, id DESC LIMIT ?",
                (limit,),
            )
            events = [self._row_to_event(row) for row in rows]
        return list(reversed(events))

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _row_to_event(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "trace_id": row["trace_id"],
            "event_type": row["event_type"],
            "timestamp": row["timestamp"],
            "payload": json.loads(row["payload"]),
            "severity": row["severity"],
            "duration_ms": row["duration_ms"],
        }

    def _ensure_column(self, table: str, column: str, column_type: str) -> None:
        existing = {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table})")
        }
        if column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
