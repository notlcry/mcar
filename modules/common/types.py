"""Common type definitions for mcar Python modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IpcError:
    code: str
    message: str
    user_message: str | None = None
    details: dict[str, Any] | None = None
    retryable: bool = False
    retry_after_ms: int | None = None


@dataclass(frozen=True)
class InvokeContext:
    invocation_id: str
    capability_id: str
    params: dict[str, Any]
    idempotency_key: str | None = None
    timeout_ms: int | None = None


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    name: str
    type: str  # "tool" | "skill"
    version: str
    description: str
    risk_level: str  # "READ_ONLY" | "NORMAL" | "DANGEROUS"
    inputs_schema: dict[str, Any] = field(default_factory=dict)
    outputs_schema: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    required_state_predicates: list[dict[str, Any]] = field(default_factory=list)
    permissions: dict[str, Any] = field(default_factory=dict)
    idempotency: dict[str, Any] = field(default_factory=dict)
    observability: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleManifest:
    module_id: str
    module_version: str
    description: str
    capabilities: list[str]
    vendor: str | None = None
    permissions_required: list[str] = field(default_factory=list)
