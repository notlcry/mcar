"""Hard safety checks for every Robot Service capability invocation."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft7Validator

from .models import CapabilitySpec, ExecutionResult, StatePredicate
from .state import RobotState


@dataclass(frozen=True)
class PolicyContext:
    role: str = "user"
    confirmed: bool = False


class ExecutionGuards:
    def __init__(self) -> None:
        self._cooldowns: dict[str, float] = {}
        self._idempotency: dict[str, float] = {}
        self._in_flight: dict[str, int] = {}
        self._mutex_locks: dict[str, str] = {}

    def before(self, spec: CapabilitySpec, params: dict[str, Any]) -> ExecutionResult | None:
        cooldown_result = self._check_cooldown(spec)
        if cooldown_result:
            return cooldown_result

        duplicate_result = self._check_idempotency(spec, params)
        if duplicate_result:
            return duplicate_result

        concurrency_result = self._check_concurrency(spec)
        if concurrency_result:
            return concurrency_result

        self._acquire(spec)
        return None

    def after(self, spec: CapabilitySpec, params: dict[str, Any]) -> None:
        cooldown_ms = spec.constraints.get("cooldown_ms")
        if isinstance(cooldown_ms, int) and cooldown_ms > 0:
            self._cooldowns[spec.capability_id] = time.monotonic() + cooldown_ms / 1000

        ttl_ms = int(spec.idempotency.get("ttl_ms") or 0)
        if spec.idempotency.get("mode") != "NONE" and ttl_ms > 0:
            key = self._idempotency_key(spec, params)
            self._idempotency[key] = time.monotonic() + ttl_ms / 1000

        self.release(spec)

    def release(self, spec: CapabilitySpec) -> None:
        concurrency = spec.constraints.get("concurrency")
        if not isinstance(concurrency, dict):
            return

        current = self._in_flight.get(spec.capability_id, 0)
        if current <= 1:
            self._in_flight.pop(spec.capability_id, None)
        else:
            self._in_flight[spec.capability_id] = current - 1

        mutex_group = concurrency.get("mutex_group")
        if mutex_group and self._mutex_locks.get(mutex_group) == spec.capability_id:
            if self._in_flight.get(spec.capability_id, 0) == 0:
                self._mutex_locks.pop(mutex_group, None)

    def _check_cooldown(self, spec: CapabilitySpec) -> ExecutionResult | None:
        expires_at = self._cooldowns.get(spec.capability_id)
        if not expires_at:
            return None

        remaining_ms = int((expires_at - time.monotonic()) * 1000)
        if remaining_ms <= 0:
            self._cooldowns.pop(spec.capability_id, None)
            return None

        return ExecutionResult.fail(
            "E_COOLDOWN_ACTIVE",
            f"Cooldown active for {spec.capability_id}",
            retryable=True,
            retry_after_ms=remaining_ms,
        )

    def _check_idempotency(
        self,
        spec: CapabilitySpec,
        params: dict[str, Any],
    ) -> ExecutionResult | None:
        now = time.monotonic()
        self._idempotency = {
            key: expiry
            for key, expiry in self._idempotency.items()
            if expiry > now
        }

        mode = spec.idempotency.get("mode")
        if mode == "NONE":
            return None

        key = self._idempotency_key(spec, params)
        if key not in self._idempotency:
            return None

        return ExecutionResult.fail(
            "E_DUPLICATE",
            f"Duplicate request for {spec.capability_id}",
            retryable=False,
        )

    def _check_concurrency(self, spec: CapabilitySpec) -> ExecutionResult | None:
        concurrency = spec.constraints.get("concurrency")
        if not isinstance(concurrency, dict):
            return None

        max_in_flight = int(concurrency.get("max_in_flight") or 1)
        current = self._in_flight.get(spec.capability_id, 0)
        if current >= max_in_flight:
            return ExecutionResult.fail(
                "E_CONCURRENCY",
                f"Max in-flight reached for {spec.capability_id}",
                retryable=True,
                retry_after_ms=500,
            )

        mutex_group = concurrency.get("mutex_group")
        holder = self._mutex_locks.get(mutex_group)
        if mutex_group and holder and holder != spec.capability_id:
            return ExecutionResult.fail(
                "E_CONCURRENCY",
                f"Mutex group {mutex_group} locked by {holder}",
                retryable=True,
                retry_after_ms=500,
            )

        return None

    def _acquire(self, spec: CapabilitySpec) -> None:
        concurrency = spec.constraints.get("concurrency")
        if not isinstance(concurrency, dict):
            return

        self._in_flight[spec.capability_id] = self._in_flight.get(spec.capability_id, 0) + 1
        mutex_group = concurrency.get("mutex_group")
        if mutex_group:
            self._mutex_locks[mutex_group] = spec.capability_id

    def _idempotency_key(self, spec: CapabilitySpec, params: dict[str, Any]) -> str:
        key_fields = spec.idempotency.get("key_fields") or []
        if not key_fields:
            return spec.capability_id
        payload = {key: params.get(key) for key in key_fields}
        return f"{spec.capability_id}:{json.dumps(payload, sort_keys=True)}"


class SafetyRouter:
    def __init__(self, state: RobotState) -> None:
        self.state = state

    def evaluate(
        self,
        spec: CapabilitySpec,
        params: dict[str, Any],
        context: PolicyContext | None = None,
    ) -> ExecutionResult | None:
        schema_error = self._validate_schema(spec, params)
        if schema_error:
            return schema_error

        policy_error = self._evaluate_policy(spec, params, context or PolicyContext())
        if policy_error:
            return policy_error

        return None

    def _validate_schema(
        self,
        spec: CapabilitySpec,
        params: dict[str, Any],
    ) -> ExecutionResult | None:
        if not spec.inputs_schema:
            return None

        validator = Draft7Validator(spec.inputs_schema)
        errors = sorted(validator.iter_errors(params), key=lambda error: list(error.path))
        if not errors:
            return None

        message = "; ".join(error.message for error in errors)
        return ExecutionResult.fail("E_INPUT_SCHEMA", f"Parameter validation failed: {message}")

    def _evaluate_policy(
        self,
        spec: CapabilitySpec,
        params: dict[str, Any],
        context: PolicyContext,
    ) -> ExecutionResult | None:
        if spec.risk_level != "READ_ONLY" and self.state.estop_locked:
            return ExecutionResult.fail(
                "E_STATE_ESTOP",
                "Emergency stop is active",
                retryable=True,
                retry_after_ms=self.state.estop_remaining_ms(),
            )

        mode = self.state.get_mode()
        if mode == "mute" and spec.permissions.get("deny_when_muted"):
            return ExecutionResult.fail(
                "E_POLICY_ROLE_DENIED",
                f"{spec.capability_id} is denied in mute mode",
            )

        for predicate in spec.required_state_predicates:
            if not self._matches(predicate):
                return ExecutionResult.fail(
                    f"E_STATE_{predicate.key.upper()}",
                    f"State predicate failed: {predicate.key} {predicate.op} {predicate.value}",
                )

        roles_allowed = spec.permissions.get("roles_allowed") or ["user", "admin"]
        if context.role not in roles_allowed:
            return ExecutionResult.fail(
                "E_POLICY_ROLE_DENIED",
                f"Role {context.role} is not allowed for {spec.capability_id}",
            )

        modes_allowed = spec.permissions.get("modes_allowed")
        if modes_allowed and mode not in modes_allowed:
            return ExecutionResult.fail(
                "E_POLICY_ROLE_DENIED",
                f"Mode {mode} is not allowed for {spec.capability_id}",
            )

        if spec.risk_level == "DANGEROUS" and spec.permissions.get("confirm_required"):
            if not context.confirmed:
                return ExecutionResult.fail(
                    "E_POLICY_CONFIRM_REQUIRED",
                    f"{spec.capability_id} requires confirmation",
                )

        if spec.capability_id.startswith("tool.motion.") and "speed" in params:
            speed = params["speed"]
            max_speed = self.state.get_max_speed()
            if isinstance(speed, int | float) and speed > max_speed:
                return ExecutionResult.fail(
                    "E_POLICY_ROLE_DENIED",
                    f"Speed {speed} exceeds max {max_speed} in {mode} mode",
                )

        return None

    def _matches(self, predicate: StatePredicate) -> bool:
        value = self.state.get(predicate.key)
        if predicate.op == "==":
            return value == predicate.value
        if predicate.op == "!=":
            return value != predicate.value
        if predicate.op == ">":
            return value > predicate.value
        if predicate.op == ">=":
            return value >= predicate.value
        if predicate.op == "<":
            return value < predicate.value
        if predicate.op == "<=":
            return value <= predicate.value
        if predicate.op == "in":
            return isinstance(predicate.value, list) and value in predicate.value
        return False
