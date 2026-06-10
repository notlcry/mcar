"""Shared models for the Python Robot Service."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["READ_ONLY", "NORMAL", "DANGEROUS"]
Mode = Literal["normal", "safety", "kid", "debug", "mute"]


class ErrorBody(BaseModel):
    code: str
    message: str
    user_message: str | None = None
    retryable: bool = False
    retry_after_ms: int | None = None


class ExecutionResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: ErrorBody | None = None
    duration_ms: int | None = None

    @classmethod
    def ok(cls, data: dict[str, Any], duration_ms: int | None = None) -> "ExecutionResult":
        return cls(success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        retryable: bool = False,
        retry_after_ms: int | None = None,
        user_message: str | None = None,
    ) -> "ExecutionResult":
        return cls(
            success=False,
            error=ErrorBody(
                code=code,
                message=message,
                user_message=user_message,
                retryable=retryable,
                retry_after_ms=retry_after_ms,
            ),
        )


class StatePredicate(BaseModel):
    key: str
    op: Literal["==", "!=", ">", ">=", "<", "<=", "in"]
    value: Any
    on_fail: Literal["DENY", "CONFIRM"] = "DENY"


class CapabilitySpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    capability_id: str
    name: str
    type: Literal["tool", "skill"]
    version: str
    description: str
    risk_level: RiskLevel
    inputs_schema: dict[str, Any] = Field(default_factory=dict)
    outputs_schema: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    required_state_predicates: list[StatePredicate] = Field(default_factory=list)
    permissions: dict[str, Any] = Field(default_factory=dict)
    idempotency: dict[str, Any] = Field(default_factory=dict)
    observability: dict[str, Any] = Field(default_factory=dict)


class ModuleManifest(BaseModel):
    module_id: str
    module_version: str
    description: str
    capabilities: list[str]
    permissions_required: list[str] = Field(default_factory=list)


class CapabilitySummary(BaseModel):
    capability_id: str
    name: str
    module_id: str
    description: str
    risk_level: RiskLevel


class ModuleSummary(BaseModel):
    module_id: str
    version: str
    description: str
    capabilities: list[str]
    enabled: bool = True


class StateSnapshot(BaseModel):
    session: str = "IDLE"
    mode: Mode = "normal"
    apiStatus: str = "online"
    obstacle: bool = False
    battery: float = 1.0
    estopLocked: bool = False
    maxSpeed: int = 100


class InvokeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    capability_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] | None = Field(default=None, alias="input")

    def invocation_params(self) -> dict[str, Any]:
        return self.params or self.input_data or {}


class ChatRequest(BaseModel):
    text: str


class ModeRequest(BaseModel):
    mode: Mode
