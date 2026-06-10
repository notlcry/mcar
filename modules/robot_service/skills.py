"""Built-in multi-step skills for Robot Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ExecutionResult


@dataclass(frozen=True)
class SkillStep:
    id: str
    capability_id: str
    params: dict[str, Any] = field(default_factory=dict)
    on_error: str = "abort"


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    version: str
    risk_level: str
    steps: list[SkillStep]
    parameters: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "parameters": self.parameters,
            "steps_count": len(self.steps),
        }


BUILTIN_SKILLS = [
    SkillDefinition(
        skill_id="skill.self_check",
        name="Self Check",
        description="Read obstacle sensors and ultrasonic distance.",
        version="1.0.0",
        risk_level="READ_ONLY",
        steps=[
            SkillStep("ultrasonic", "tool.sensor.ultrasonic", on_error="skip"),
            SkillStep("infrared", "tool.sensor.infrared", on_error="skip"),
        ],
    ),
    SkillDefinition(
        skill_id="skill.night_mode",
        name="Night Mode",
        description="Show sleeping expression and enter mute mode.",
        version="1.0.0",
        risk_level="NORMAL",
        steps=[
            SkillStep(
                "show_sleeping",
                "tool.display.show_expression",
                {"expression": "sleeping"},
                on_error="skip",
            ),
            SkillStep("set_mute", "system.set_mode", {"mode": "mute"}),
        ],
    ),
    SkillDefinition(
        skill_id="skill.patrol",
        name="Patrol",
        description="Simple forward-and-turn patrol sequence.",
        version="1.0.0",
        risk_level="DANGEROUS",
        parameters={"speed": {"type": "integer", "default": 30}},
        steps=[
            SkillStep("check_obstacle", "tool.sensor.infrared"),
            SkillStep(
                "move_forward",
                "tool.motion.forward",
                {"speed": "${speed}", "duration_ms": 500},
            ),
            SkillStep("turn", "tool.motion.turn_right", {"speed": "${speed}", "duration_ms": 300}),
        ],
    ),
]


class SkillEngine:
    def __init__(self, service: Any) -> None:
        self._service = service
        self._skills = {skill.skill_id: skill for skill in BUILTIN_SKILLS}

    def list(self) -> list[dict[str, Any]]:
        return [skill.summary() for skill in self._skills.values()]

    async def execute(
        self,
        skill_id: str,
        params: dict[str, Any] | None = None,
        *,
        role: str = "user",
        confirmed: bool = False,
    ) -> dict[str, Any]:
        resolved_id = self._resolve_skill_id(skill_id)
        skill = self._skills.get(resolved_id)
        if not skill:
            return self._failure(skill_id, 0, 0, {}, f"Skill not found: {skill_id}")
        if skill.risk_level == "DANGEROUS" and not confirmed:
            return self._failure(
                resolved_id,
                0,
                len(skill.steps),
                {},
                f"Skill {resolved_id} requires confirmation",
            )

        params = self._with_defaults(skill, params or {})
        results: dict[str, Any] = {}
        completed = 0
        for step in skill.steps:
            resolved_params = self._resolve_params(step.params, params)
            result = await self._execute_step(step.capability_id, resolved_params)
            if result.success:
                results[step.id] = result.data
                completed += 1
                continue

            error = result.error.message if result.error else "Unknown error"
            if step.on_error == "skip":
                results[step.id] = {"skipped": True, "error": error}
                completed += 1
                continue

            return self._failure(
                skill_id,
                completed,
                len(skill.steps),
                results,
                f"Step {step.id} failed: {error}",
                aborted_at_step=step.id,
            )

        return {
            "skill_id": resolved_id,
            "success": True,
            "steps_completed": completed,
            "steps_total": len(skill.steps),
            "results": results,
        }

    def _resolve_skill_id(self, skill_id: str) -> str:
        if skill_id in self._skills:
            return skill_id
        prefixed = f"skill.{skill_id}"
        if prefixed in self._skills:
            return prefixed
        return skill_id

    async def _execute_step(self, capability_id: str, params: dict[str, Any]) -> ExecutionResult:
        if capability_id == "system.set_mode":
            result = self._service.set_mode(params["mode"])
            return ExecutionResult.ok(result)
        return await self._service.invoke(capability_id, params)

    def _with_defaults(
        self,
        skill: SkillDefinition,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(params)
        for name, schema in skill.parameters.items():
            if name not in merged and isinstance(schema, dict) and "default" in schema:
                merged[name] = schema["default"]
        return merged

    def _resolve_params(
        self,
        step_params: dict[str, Any],
        skill_params: dict[str, Any],
    ) -> dict[str, Any]:
        resolved = dict(step_params)
        for key, value in resolved.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                resolved[key] = skill_params.get(value[2:-1])
        return resolved

    def _failure(
        self,
        skill_id: str,
        completed: int,
        total: int,
        results: dict[str, Any],
        error: str,
        aborted_at_step: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "skill_id": skill_id,
            "success": False,
            "steps_completed": completed,
            "steps_total": total,
            "results": results,
            "error": error,
        }
        if aborted_at_step:
            payload["aborted_at_step"] = aborted_at_step
        return payload
