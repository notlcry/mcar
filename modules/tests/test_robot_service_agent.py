"""Tests for the Pydantic AI robot agent boundary."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import pytest
from pydantic import ValidationError

from robot_service.agent import MoveCommand, build_agent_model
from robot_service.__main__ import resolve_model
from robot_service.service import create_robot_service


def test_move_command_rejects_unsafe_duration() -> None:
    with pytest.raises(ValidationError):
        MoveCommand(direction="forward", duration_ms=1500, speed=30)


def test_move_command_rejects_unsafe_speed() -> None:
    with pytest.raises(ValidationError):
        MoveCommand(direction="forward", duration_ms=500, speed=80)


def test_resolve_model_supports_openai_compatible_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.5")

    assert resolve_model() == "openai-compatible:gpt-5.5"


def test_build_agent_model_uses_openai_compatible_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://proxy.198437.xyz/v1")
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")

    model = build_agent_model("openai-compatible:gpt-5.5")

    assert model.model_name == "gpt-5.5"
    assert str(model.provider.base_url) == "https://proxy.198437.xyz/v1/"
    assert model.__class__.__name__ == "StreamingOpenAIChatModel"


def test_build_agent_model_accepts_dashscope_key_for_openai_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("PROXY_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")

    model = build_agent_model("openai-compatible:qwen-plus")

    assert model.model_name == "qwen-plus"
    assert model.__class__.__name__ == "StreamingOpenAIChatModel"


def test_dashscope_base_url_prefers_dashscope_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")

    model = build_agent_model("openai-compatible:qwen3.6-flash")

    assert model.provider.client.api_key == "dashscope-key"


@pytest.mark.asyncio
async def test_openai_compatible_model_request_consumes_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://proxy.198437.xyz/v1")
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")
    model = build_agent_model("openai-compatible:gpt-5.5")
    seen_chunks: list[str] = []

    class FakeStream:
        def __init__(self) -> None:
            self._pending = ["first", "second"]

        def __aiter__(self) -> "FakeStream":
            return self

        async def __anext__(self) -> str:
            if not self._pending:
                raise StopAsyncIteration
            chunk = self._pending.pop(0)
            seen_chunks.append(chunk)
            return chunk

        def get(self) -> str:
            return "complete-response"

    @asynccontextmanager
    async def fake_request_stream(*args: Any, **kwargs: Any):
        yield FakeStream()

    monkeypatch.setattr(model, "request_stream", fake_request_stream)

    response = await model.request([], None, object())

    assert response == "complete-response"
    assert seen_chunks == ["first", "second"]


def test_build_agent_model_ignores_socks_proxy_env_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://proxy.198437.xyz/v1")
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")
    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:1080")

    model = build_agent_model("openai-compatible:gpt-5.5")

    assert model.model_name == "gpt-5.5"


def test_robot_agent_registers_tools_with_runtime_type_hints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://proxy.198437.xyz/v1")
    monkeypatch.setenv("PROXY_API_KEY", "proxy-key")
    service = create_robot_service(mock=True, agent_model="openai-compatible:gpt-5.5")

    agent = service.agent._create_agent()

    assert agent is not None


@pytest.mark.asyncio
async def test_move_command_routes_through_robot_service_safety() -> None:
    service = create_robot_service(mock=True)
    service.state.set("obstacle", True)

    result = await service.move(MoveCommand(direction="forward", duration_ms=500, speed=30))

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "E_STATE_OBSTACLE"
