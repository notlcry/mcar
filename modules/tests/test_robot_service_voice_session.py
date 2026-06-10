"""Tests for Robot Service voice conversation sessions."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from robot_service.agent import MoveCommand
from robot_service.models import ExecutionResult
from robot_service.service import RobotService, create_robot_service


def _patch_voice_turn(
    service: RobotService,
    *,
    recognized: dict[str, Any],
    response: str = "收到",
) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_voice_invoke(
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append((capability_id, dict(params)))
        if capability_id == "tool.voice.recognize":
            return recognized
        if capability_id == "tool.voice.synthesize":
            return {
                "ok": True,
                "duration_ms": 10,
                "provider": "aliyun_qwen_tts_realtime",
                "model": "qwen3-tts-flash-realtime",
                "voice": params.get("voice"),
            }
        if capability_id == "tool.voice.play_prompt":
            return {"ok": True, "duration_ms": 100, "prompt": params.get("prompt")}
        if capability_id == "tool.voice.listen_start":
            return {"ok": True, "listening": True}
        if capability_id == "tool.voice.listen_stop":
            return {"ok": True}
        raise AssertionError(f"unexpected voice capability: {capability_id}")

    async def fake_chat(text: str) -> str:
        calls.append(("chat", {"text": text}))
        return response

    service.modules.voice.invoke = fake_voice_invoke
    service.chat = fake_chat  # type: ignore[method-assign]
    return calls


def _patch_voice_turns(
    service: RobotService,
    *,
    recognized: list[dict[str, Any]],
    response: str = "收到",
) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    recognitions = list(recognized)

    async def fake_voice_invoke(
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append((capability_id, dict(params)))
        if capability_id == "tool.voice.recognize":
            return recognitions.pop(0)
        if capability_id == "tool.voice.synthesize":
            return {
                "ok": True,
                "duration_ms": 10,
                "provider": "aliyun_qwen_tts_realtime",
                "model": "qwen3-tts-flash-realtime",
                "voice": params.get("voice"),
            }
        if capability_id == "tool.voice.play_prompt":
            return {"ok": True, "duration_ms": 100, "prompt": params.get("prompt")}
        if capability_id == "tool.voice.listen_start":
            return {"ok": True, "listening": True}
        if capability_id == "tool.voice.listen_stop":
            return {"ok": True}
        raise AssertionError(f"unexpected voice capability: {capability_id}")

    async def fake_chat(text: str) -> str:
        calls.append(("chat", {"text": text}))
        return response

    service.modules.voice.invoke = fake_voice_invoke
    service.chat = fake_chat  # type: ignore[method-assign]
    return calls


def _patch_display(
    service: RobotService,
) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_display_invoke(
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append((capability_id, dict(params)))
        if capability_id == "tool.display.show_expression":
            return {"ok": True, "expression": params.get("expression")}
        if capability_id == "tool.display.show_text":
            return {"ok": True, "lines_shown": 2}
        raise AssertionError(f"unexpected display capability: {capability_id}")

    service.modules.display.invoke = fake_display_invoke
    return calls


@pytest.mark.asyncio
async def test_voice_session_runs_asr_chat_tts_and_resumes_listening(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={
            "ok": True,
            "text": "看一下状态",
            "confidence": 0.9,
            "metadata": {
                "provider": "aliyun_funasr_realtime",
                "mode": "streaming",
                "first_package_delay_ms": 120,
            },
        },
        response="状态正常",
    )

    result = await service.voice_session.run_once(source="test")

    assert result == {"ok": True, "text": "看一下状态", "response": "状态正常"}
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
        (
            "chat",
            {
                "text": (
                    "看一下状态\n\n"
                    "语音回复要求：请用一句话直接回答，不解释过程，"
                    "最多 80 个中文字。"
                )
            },
        ),
        ("tool.voice.synthesize", {"text": "状态正常", "voice": "zh-CN-XiaoxiaoNeural"}),
        ("tool.voice.listen_start", {}),
    ]
    events = service.audit_events(limit=20)
    ok_event = next(event for event in events if event["event_type"] == "voice.turn.ok")
    timing = ok_event["payload"]["timing"]
    assert timing["asr_ms"] >= 0
    assert timing["llm_ms"] >= 0
    assert timing["tts_ms"] >= 0
    assert timing["total_ms"] >= 0
    assert ok_event["payload"]["asr"] == {
        "confidence": 0.9,
        "metadata": {
            "provider": "aliyun_funasr_realtime",
            "mode": "streaming",
            "first_package_delay_ms": 120,
        },
    }
    assert ok_event["payload"]["llm"] == {"model": service.agent.model}
    assert ok_event["payload"]["tts"] == {
        "provider": "aliyun_qwen_tts_realtime",
        "model": "qwen3-tts-flash-realtime",
        "voice": "zh-CN-XiaoxiaoNeural",
    }


@pytest.mark.asyncio
async def test_voice_session_uses_longer_default_voice_reply_limit(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "讲长一点", "confidence": 0.9},
        response="一二三四五六七八九十" * 6,
    )

    result = await service.voice_session.run_once(source="test")

    chat_call = next(params for name, params in calls if name == "chat")
    assert "最多 80 个中文字" in chat_call["text"]
    assert len(result["response"]) == 60


@pytest.mark.asyncio
async def test_voice_session_updates_display_status(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "看一下状态", "confidence": 0.9},
        response="状态正常",
    )
    display_calls = _patch_display(service)

    result = await service.voice_session.run_once(source="test")

    assert result["ok"] is True
    expression_calls = [
        params["expression"]
        for capability_id, params in display_calls
        if capability_id == "tool.display.show_expression"
    ]
    assert expression_calls == ["listening", "thinking", "speaking", "sleeping"]
    text_calls = [
        params["text"]
        for capability_id, params in display_calls
        if capability_id == "tool.display.show_text"
    ]
    assert text_calls[-1] == "SLEEP\nSay hey_jarvis"


@pytest.mark.asyncio
async def test_voice_session_executes_local_motion_command_without_llm(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "向前走一点", "confidence": 0.9},
    )
    moved: list[MoveCommand] = []

    async def fake_move(command: MoveCommand) -> ExecutionResult:
        moved.append(command)
        return ExecutionResult.ok({"ok": True, "actual_duration_ms": command.duration_ms})

    service.move = fake_move  # type: ignore[method-assign]

    result = await service.voice_session.run_once(source="test")

    assert result["ok"] is True
    assert result["handled_locally"] is True
    assert result["command"] == "move"
    assert moved == [MoveCommand(direction="forward", duration_ms=500, speed=25)]
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
        ("tool.voice.listen_start", {}),
    ]
    events = service.audit_events(limit=10)
    command_event = next(event for event in events if event["event_type"] == "voice.turn.command")
    assert command_event["payload"]["command"] == "move"
    assert command_event["payload"]["timing"]["action_ms"] >= 0


@pytest.mark.asyncio
async def test_voice_session_executes_local_routine_without_llm(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "跳个舞", "confidence": 0.9},
    )
    moved: list[MoveCommand] = []

    async def fake_move(command: MoveCommand) -> ExecutionResult:
        moved.append(command)
        return ExecutionResult.ok({"ok": True, "actual_duration_ms": command.duration_ms})

    service.move = fake_move  # type: ignore[method-assign]

    result = await service.voice_session.run_once(source="test")

    assert result["ok"] is True
    assert result["handled_locally"] is True
    assert result["command"] == "routine"
    assert result["routine"] == "dance"
    assert len(moved) > 1
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
        ("tool.voice.listen_start", {}),
    ]
    events = service.audit_events(limit=10)
    command_event = next(event for event in events if event["event_type"] == "voice.turn.command")
    assert command_event["payload"]["command"] == "routine"
    assert command_event["payload"]["routine"] == "dance"
    assert command_event["payload"]["step_count"] == len(moved)


@pytest.mark.asyncio
async def test_voice_session_ignores_known_asr_noise_without_llm(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "转款。", "confidence": 0.9},
    )

    async def fail_chat(text: str) -> str:
        raise AssertionError(f"unexpected chat call: {text}")

    service.chat = fail_chat  # type: ignore[method-assign]

    result = await service.voice_session.run_once(source="test")

    assert result == {"ok": False, "reason": "ignored_asr_noise", "text": "转款。"}
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
        ("tool.voice.listen_start", {}),
    ]
    events = service.audit_events(limit=10)
    ignored_event = next(event for event in events if event["event_type"] == "voice.turn.ignored")
    assert ignored_event["payload"]["reason"] == "ignored_asr_noise"
    assert ignored_event["payload"]["text"] == "转款。"


@pytest.mark.asyncio
async def test_voice_session_plays_ack_and_limits_voice_reply(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOICE_ACK_ENABLED", "true")
    monkeypatch.setenv("VOICE_ACK_TEXT", "我在。")
    monkeypatch.setenv("VOICE_REPLY_MAX_CHARS", "6")
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "看一下状态", "confidence": 0.9},
        response="这是一个很长很长的回复",
    )

    result = await service.voice_session.run_once(source="test")

    chat_call = next(params for name, params in calls if name == "chat")
    tts_calls = [params for name, params in calls if name == "tool.voice.synthesize"]
    assert result == {"ok": True, "text": "看一下状态", "response": "这是一个很长"}
    assert "看一下状态" in chat_call["text"]
    assert "最多 6 个中文字" in chat_call["text"]
    assert tts_calls == [
        {"text": "我在。", "voice": "zh-CN-XiaoxiaoNeural"},
        {"text": "这是一个很长", "voice": "zh-CN-XiaoxiaoNeural"},
    ]


@pytest.mark.asyncio
async def test_voice_session_starts_asr_without_waiting_for_ack(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOICE_ACK_ENABLED", "true")
    service = create_robot_service(mock=True, data_dir=tmp_path)
    ack_started = asyncio.Event()
    recognize_started = asyncio.Event()
    release_ack = asyncio.Event()

    async def fake_voice_invoke(
        capability_id: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if capability_id == "tool.voice.listen_stop":
            return {"ok": True}
        if capability_id == "tool.voice.listen_start":
            return {"ok": True, "listening": True}
        if capability_id == "tool.voice.play_prompt":
            return {"ok": True, "duration_ms": 100, "prompt": params.get("prompt")}
        if capability_id == "tool.voice.synthesize" and params["text"] == "我在。":
            ack_started.set()
            await release_ack.wait()
            return {"ok": True, "duration_ms": 10}
        if capability_id == "tool.voice.synthesize":
            return {"ok": True, "duration_ms": 10}
        if capability_id == "tool.voice.recognize":
            recognize_started.set()
            release_ack.set()
            return {"ok": True, "text": "看一下状态"}
        raise AssertionError(f"unexpected voice capability: {capability_id}")

    async def fake_chat(text: str) -> str:
        return "状态正常"

    service.modules.voice.invoke = fake_voice_invoke
    service.chat = fake_chat  # type: ignore[method-assign]

    task = asyncio.create_task(service.voice_session.run_once(source="test"))
    await asyncio.wait_for(ack_started.wait(), timeout=0.2)
    await asyncio.wait_for(recognize_started.wait(), timeout=0.2)

    result = await task
    assert result == {"ok": True, "text": "看一下状态", "response": "状态正常"}


@pytest.mark.asyncio
async def test_voice_session_uses_env_command_timeout(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOICE_COMMAND_TIMEOUT_S", "30")
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "看一下状态", "confidence": 0.9},
    )

    await service.voice_session.run_once(source="test")

    assert ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}) in calls


def test_voice_session_accepts_long_follow_up_window(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOICE_FOLLOW_UP_ENABLED", "true")
    monkeypatch.setenv("VOICE_FOLLOW_UP_TIMEOUT_S", "30")
    monkeypatch.setenv("VOICE_FOLLOW_UP_MAX_TURNS", "50")

    service = create_robot_service(mock=True, data_dir=tmp_path)

    assert service.voice_session.config_payload()["follow_up_timeout_s"] == 30
    assert service.voice_session.config_payload()["follow_up_max_turns"] == 50


@pytest.mark.asyncio
async def test_voice_session_runs_follow_up_turn_without_wake_prompt(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOICE_FOLLOW_UP_ENABLED", "true")
    monkeypatch.setenv("VOICE_FOLLOW_UP_MAX_TURNS", "1")
    monkeypatch.setenv("VOICE_FOLLOW_UP_TIMEOUT_S", "3")
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turns(
        service,
        recognized=[
            {"ok": True, "text": "你在干什么", "confidence": 0.9},
            {"ok": True, "text": "前进", "confidence": 0.9},
        ],
        response="我在待命",
    )
    moved: list[MoveCommand] = []

    async def fake_move(command: MoveCommand) -> ExecutionResult:
        moved.append(command)
        return ExecutionResult.ok({"ok": True, "actual_duration_ms": command.duration_ms})

    service.move = fake_move  # type: ignore[method-assign]

    result = await service.voice_session.run_once(source="test")

    assert result["ok"] is True
    assert result["follow_up"][0]["command"] == "move"
    assert moved == [MoveCommand(direction="forward", duration_ms=500, speed=25)]
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
        (
            "chat",
            {
                "text": (
                    "你在干什么\n\n"
                    "语音回复要求：请用一句话直接回答，不解释过程，"
                    "最多 80 个中文字。"
                )
            },
        ),
        ("tool.voice.synthesize", {"text": "我在待命", "voice": "zh-CN-XiaoxiaoNeural"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 3}),
        ("tool.voice.listen_start", {}),
    ]
    events = service.audit_events(limit=20)
    assert any(
        event["event_type"] == "voice.turn.command"
        and event["payload"]["source"] == "test:follow_up_1"
        and event["payload"]["direction"] == "forward"
        for event in events
    )


@pytest.mark.asyncio
async def test_voice_session_stop_word_triggers_estop_without_response_or_resume(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "停止", "is_stop_word": True},
    )

    result = await service.voice_session.run_once(source="test")

    assert result == {"ok": True, "stopped": True}
    assert service.state.estop_locked is True
    assert calls == [
        ("tool.voice.listen_stop", {}),
        ("tool.voice.play_prompt", {"prompt": "wake"}),
        ("tool.voice.recognize", {"language": "zh-CN", "timeout_s": 30}),
    ]


@pytest.mark.asyncio
async def test_voice_driver_wake_callback_starts_voice_session(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)
    calls = _patch_voice_turn(
        service,
        recognized={"ok": True, "text": "你好", "confidence": 0.9},
        response="你好",
    )

    assert service.modules.voice.driver._on_wake_word is not None
    await service.modules.voice.driver._on_wake_word()
    await service.voice_session.wait_idle()

    assert any(name == "chat" and params["text"].startswith("你好") for name, params in calls)


@pytest.mark.asyncio
async def test_voice_driver_stop_callback_triggers_estop(tmp_path) -> None:
    service = create_robot_service(mock=True, data_dir=tmp_path)

    assert service.modules.voice.driver._on_stop_word is not None
    await service.modules.voice.driver._on_stop_word()

    assert service.state.estop_locked is True
