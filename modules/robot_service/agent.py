"""Pydantic AI agent boundary for robot decisions."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from .models import ExecutionResult

try:
    from pydantic_ai import Agent, RunContext
    from pydantic_ai.exceptions import UserError
    from pydantic_ai.models.openai import OpenAIChatModel
except ImportError:
    Agent = None
    RunContext = Any
    UserError = ValueError
    OpenAIChatModel = None

if TYPE_CHECKING:
    from .service import RobotService


class MoveCommand(BaseModel):
    direction: Literal["forward", "backward", "left", "right"]
    duration_ms: int = Field(ge=100, le=1000)
    speed: int = Field(ge=10, le=40)


class RobotAgent:
    def __init__(self, service: "RobotService", model: str = "google:gemini-2.5-flash") -> None:
        self.service = service
        self.model = model
        self._agent = None

    async def chat(self, text: str) -> str:
        if self._agent is None:
            self._agent = self._create_agent()
        if not self._agent:
            return "我现在可以执行机器人动作，但未启用 LLM。"

        result = await self._agent.run(text, deps=self.service)
        return str(result.output)

    def _create_agent(self):
        if Agent is None:
            return None

        try:
            agent = Agent(
                build_agent_model(self.model),
                deps_type=type(self.service),
                instructions=self._instructions(),
            )
        except (UserError, ValueError):
            return None

        @agent.tool
        async def move(ctx: RunContext[Any], command: MoveCommand) -> dict:
            """Move the robot using a bounded command."""
            result = await ctx.deps.move(command)
            return result.model_dump(exclude_none=True)

        @agent.tool
        async def stop(ctx: RunContext[Any]) -> dict:
            """Immediately stop all robot motion."""
            return await ctx.deps.trigger_stop("agent")

        @agent.tool
        async def read_status(ctx: RunContext[Any]) -> dict:
            """Read the current robot state and module status."""
            return ctx.deps.status()

        return agent

    def _instructions(self) -> str:
        return (
            "You control a small Raspberry Pi robot. "
            "All physical actions must use tools. "
            "Never ask tools to exceed their typed bounds. "
            "Emergency stop must be used immediately when the user asks to stop."
        )


if OpenAIChatModel is not None:

    class StreamingOpenAIChatModel(OpenAIChatModel):
        async def request(
            self,
            messages: list[Any],
            model_settings: Any,
            model_request_parameters: Any,
        ) -> Any:
            async with self.request_stream(
                messages,
                model_settings,
                model_request_parameters,
            ) as response:
                async for _ in response:
                    pass
                return response.get()

else:
    StreamingOpenAIChatModel = None


async def execute_move(service: "RobotService", command: MoveCommand) -> ExecutionResult:
    return await service.move(command)


def build_agent_model(model: str):
    provider, model_name = _split_model(model)
    if provider in {"openai-compatible", "openai_compatible"}:
        return _openai_compatible_model(model_name)
    if provider == "openai" and os.environ.get("LLM_BASE_URL"):
        return _openai_compatible_model(model_name)
    return model


def _split_model(model: str) -> tuple[str | None, str]:
    if ":" not in model:
        return None, model
    provider, model_name = model.split(":", 1)
    return provider.strip().lower(), model_name.strip()


def _openai_compatible_model(model_name: str):
    import httpx

    from pydantic_ai.providers.openai import OpenAIProvider

    base_url = _required_env("LLM_BASE_URL")
    api_key = _openai_compatible_api_key(base_url)
    if not api_key:
        raise ValueError(
            "LLM_API_KEY, PROXY_API_KEY, OPENAI_API_KEY, or DASHSCOPE_API_KEY is required"
        )
    if StreamingOpenAIChatModel is None:
        raise ValueError("pydantic-ai OpenAI support is required")
    http_client = httpx.AsyncClient(
        trust_env=_env_bool(os.environ.get("LLM_HTTP_TRUST_ENV", "false")),
    )
    return StreamingOpenAIChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key, http_client=http_client),
    )


def _openai_compatible_api_key(base_url: str) -> str | None:
    normalized = base_url.strip().lower()
    if "dashscope" in normalized or "aliyuncs.com" in normalized:
        return _first_env("LLM_API_KEY", "DASHSCOPE_API_KEY")
    return _first_env("LLM_API_KEY", "PROXY_API_KEY", "OPENAI_API_KEY", "DASHSCOPE_API_KEY")


def _required_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _first_env(*keys: str) -> str | None:
    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
