"""Helper for building capability spec dicts from JSON files or inline definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_capabilities(json_path: str | Path) -> list[dict[str, Any]]:
    """Load capability specs from a JSON file."""
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "capabilities" in data:
        return data["capabilities"]
    raise ValueError(f"Invalid capabilities file: {path}")


def build_capability(
    capability_id: str,
    name: str,
    description: str,
    risk_level: str = "READ_ONLY",
    cap_type: str = "tool",
    version: str = "1.0.0",
    inputs_schema: dict[str, Any] | None = None,
    outputs_schema: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    required_state_predicates: list[dict[str, Any]] | None = None,
    permissions: dict[str, Any] | None = None,
    idempotency: dict[str, Any] | None = None,
    observability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a capability spec dict with sensible defaults."""
    return {
        "capability_id": capability_id,
        "name": name,
        "type": cap_type,
        "version": version,
        "description": description,
        "risk_level": risk_level,
        "inputs_schema": inputs_schema or {"type": "object", "properties": {}},
        "outputs_schema": outputs_schema or {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        "constraints": constraints or {"timeout_ms": 5000},
        "required_state_predicates": required_state_predicates or [],
        "permissions": permissions or {
            "roles_allowed": ["user", "admin"],
            "confirm_required": False,
        },
        "idempotency": idempotency or {
            "mode": "NONE",
            "key_fields": [],
            "ttl_ms": 0,
        },
        "observability": observability or {
            "audit_level": "STANDARD",
            "log_inputs": True,
            "log_outputs": True,
            "redaction": [],
        },
    }
