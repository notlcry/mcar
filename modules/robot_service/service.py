"""Main Python Robot Service orchestration layer."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .adapters import RobotModules
from .agent import MoveCommand, RobotAgent
from .command_parser import RoutineCommand, parse_local_command
from .models import ExecutionResult, Mode
from .registry import CapabilityRegistry
from .rules import RuleEngine
from .safety import ExecutionGuards, PolicyContext, SafetyRouter
from .skills import SkillEngine
from .state import RobotState
from .storage import AuditStore, MemoryStore
from .voice_session import VoiceSession

STOP_WORDS = {"stop", "halt", "emergency", "停", "停止", "急停"}

_SESSION_DISPLAY: dict[str, tuple[str, str]] = {
    "IDLE": ("sleeping", "SLEEP\nSay hey_jarvis"),
    "LISTENING": ("listening", "LISTENING\nSpeak now"),
    "THINKING": ("thinking", "THINKING"),
    "RESPONDING": ("speaking", "SPEAKING"),
    "ACTING": ("excited", "ACTING"),
    "STOPPED": ("sad", "STOPPED\nSafety lock"),
}


class RobotService:
    def __init__(
        self,
        modules: RobotModules,
        state: RobotState,
        registry: CapabilityRegistry,
        safety: SafetyRouter,
        guards: ExecutionGuards,
        memory: MemoryStore,
        audit_store: AuditStore,
        agent_model: str = "google:gemini-2.5-flash",
    ) -> None:
        self.modules = modules
        self.state = state
        self.registry = registry
        self.safety = safety
        self.guards = guards
        self.memory = memory
        self.audit_store = audit_store
        self.skills = SkillEngine(self)
        self.rules = RuleEngine(self)
        self.agent = RobotAgent(self, model=agent_model)
        self.voice_session = VoiceSession(self)
        self.voice_session.attach()
        self._started_at = time.monotonic()
        self._last_display_session: str | None = None

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any] | None = None,
        *,
        role: str = "user",
        confirmed: bool = False,
    ) -> ExecutionResult:
        params = params or {}
        registered = self.registry.get(capability_id)
        if not registered:
            return ExecutionResult.fail("E_NOT_FOUND", f"Capability not found: {capability_id}")

        policy_error = self.safety.evaluate(
            registered.spec,
            params,
            PolicyContext(role=role, confirmed=confirmed),
        )
        if policy_error:
            self._audit(
                "invoke.denied",
                {"capability_id": capability_id, "error": policy_error.error.model_dump()},
            )
            return policy_error

        guard_error = self.guards.before(registered.spec, params)
        if guard_error:
            self._audit(
                "invoke.denied",
                {"capability_id": capability_id, "error": guard_error.error.model_dump()},
            )
            return guard_error

        start = time.monotonic()
        try:
            data = await registered.module.invoke(
                capability_id,
                params,
                {
                    "invocation_id": str(uuid.uuid4()),
                    "timeout_ms": registered.spec.constraints.get("timeout_ms"),
                },
            )
            self._update_state_from_result(capability_id, data)
            duration_ms = int((time.monotonic() - start) * 1000)
            self._audit("invoke.ok", {"capability_id": capability_id, "duration_ms": duration_ms})
            return ExecutionResult.ok(data, duration_ms=duration_ms)
        except Exception as exc:
            self._audit("invoke.error", {"capability_id": capability_id, "error": str(exc)})
            return ExecutionResult.fail("E_INTERNAL", str(exc), retryable=False)
        finally:
            self.guards.after(registered.spec, params)

    async def move(self, command: MoveCommand) -> ExecutionResult:
        capability_id = {
            "forward": "tool.motion.forward",
            "backward": "tool.motion.backward",
            "left": "tool.motion.turn_left",
            "right": "tool.motion.turn_right",
        }[command.direction]
        return await self.invoke(
            capability_id,
            {
                "speed": command.speed,
                "duration_ms": command.duration_ms,
            },
        )

    async def run_routine(self, routine: RoutineCommand) -> ExecutionResult:
        start = time.monotonic()
        steps: list[dict[str, Any]] = []
        step_count = len(routine.steps)
        for index, command in enumerate(routine.steps, start=1):
            result = await self.move(command)
            steps.append(
                {
                    "index": index,
                    "direction": command.direction,
                    "duration_ms": command.duration_ms,
                    "speed": command.speed,
                    "success": result.success,
                }
            )
            if not result.success:
                error = result.error.message if result.error else "routine step failed"
                return ExecutionResult.fail(
                    "E_ROUTINE_STEP_FAILED",
                    f"{routine.name} step {index} failed: {error}",
                    retryable=False,
                )
            if index < step_count:
                await asyncio.sleep(0.22)
        return ExecutionResult.ok(
            {
                "ok": True,
                "routine": routine.name,
                "step_count": len(steps),
                "steps": steps,
            },
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    async def set_session_state(self, session: str) -> None:
        self.state.set("session", session)
        await self._show_session_display(session)

    async def _show_session_display(self, session: str) -> None:
        if not _env_bool(os.environ.get("VOICE_DISPLAY_STATUS_ENABLED", "true")):
            return
        if self._last_display_session == session:
            return
        display = _SESSION_DISPLAY.get(session)
        if display is None:
            return
        expression, text = display
        context = {"invocation_id": str(uuid.uuid4())}
        expression_result = await self.modules.display.invoke(
            "tool.display.show_expression",
            {"expression": expression},
            context,
        )
        text_result = await self.modules.display.invoke(
            "tool.display.show_text",
            {"text": text, "font_size": 12},
            {"invocation_id": str(uuid.uuid4())},
        )
        self._last_display_session = session
        self._audit(
            "display.status",
            {
                "session": session,
                "expression": expression,
                "expression_ok": bool(expression_result.get("ok")),
                "text_ok": bool(text_result.get("ok")),
            },
        )

    async def trigger_stop(self, source: str) -> dict[str, Any]:
        for module in self.modules.all():
            await module.stop()
        self.state.lock_estop()
        await self.set_session_state("STOPPED")
        self._audit("stop", {"source": source})
        return {"ok": True, "source": source}

    async def chat(self, text: str) -> str:
        if text.strip().lower() in STOP_WORDS:
            await self.trigger_stop("chat")
            return "已急停。"
        local_command = parse_local_command(text)
        if local_command is not None:
            if local_command.kind == "stop":
                await self.trigger_stop("chat")
                return "已停止。"
            if local_command.kind == "move" and local_command.move is not None:
                result = await self.move(local_command.move)
                if result.success:
                    return "执行完毕。"
                if result.error:
                    return f"执行失败：{result.error.message}"
                return "执行失败。"
            if local_command.kind == "routine" and local_command.routine is not None:
                result = await self.run_routine(local_command.routine)
                if result.success:
                    return "执行完毕。"
                if result.error:
                    return f"执行失败：{result.error.message}"
                return "执行失败。"
        return await self.agent.chat(text)

    def set_mode(self, mode: Mode) -> dict[str, Any]:
        self.state.set_mode(mode)
        return {"ok": True, "mode": mode}

    def status(self) -> dict[str, Any]:
        snapshot = self.state.snapshot().model_dump()
        snapshot["registeredModules"] = [module.module_id for module in self.registry.modules()]
        return snapshot

    def health(self) -> dict[str, Any]:
        return {
            "overall": "ok",
            "modules": [module.model_dump() for module in self.registry.modules()],
            "uptime_ms": int((time.monotonic() - self._started_at) * 1000),
            "timestamp": time.time(),
        }

    def audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit_store.recent(limit)

    def _update_state_from_result(self, capability_id: str, data: dict[str, Any]) -> None:
        if capability_id == "tool.sensor.infrared" and data.get("ok"):
            obstacle = bool(data.get("left_obstacle")) or bool(data.get("right_obstacle"))
            self.state.set("obstacle", obstacle)
        if capability_id == "tool.sensor.ultrasonic" and data.get("ok"):
            distance = data.get("distance_cm")
            if isinstance(distance, int | float):
                self.state.set("obstacle", distance < 15)

    def audit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._audit(event_type, payload)

    def _audit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.audit_store.log(event_type, payload)


def create_robot_service(
    *,
    mock: bool = False,
    estop_cooldown_ms: int = 2000,
    agent_model: str = "google:gemini-2.5-flash",
    data_dir: str | Path | None = None,
) -> RobotService:
    data_path = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "data"
    modules = RobotModules(mock=mock)
    state = RobotState(estop_cooldown_ms=estop_cooldown_ms)
    registry = CapabilityRegistry(modules.all())
    return RobotService(
        modules=modules,
        state=state,
        registry=registry,
        safety=SafetyRouter(state),
        guards=ExecutionGuards(),
        memory=MemoryStore(data_path / "memory.db"),
        audit_store=AuditStore(data_path / "audit.db"),
        agent_model=agent_model,
    )


def _env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
