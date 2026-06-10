"""Tests for the voice E2E probe helper script."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "voice_e2e_probe.py"
spec = importlib.util.spec_from_file_location("voice_e2e_probe", SCRIPT_PATH)
assert spec is not None
voice_e2e_probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(voice_e2e_probe)


def test_summarize_voice_event_includes_timing_and_provider_metadata() -> None:
    event = {
        "id": "evt-1",
        "event_type": "voice.turn.ok",
        "timestamp": "2026-06-10T10:00:00Z",
        "payload": {
            "source": "e2e_probe",
            "text": "看一下状态",
            "timing": {"prompt_ms": 20, "asr_ms": 900, "llm_ms": 300, "tts_ms": 500, "total_ms": 1720},
            "asr": {"metadata": {"provider": "aliyun_funasr_realtime", "mode": "streaming"}},
            "llm": {"model": "openai-compatible:gpt-5.5"},
            "tts": {"provider": "aliyun_qwen_tts_realtime", "model": "qwen3-tts-flash-realtime"},
        },
    }

    summary = voice_e2e_probe.summarize_voice_event(event, request_ms=1800)

    assert summary == {
        "event_id": "evt-1",
        "event_type": "voice.turn.ok",
        "timestamp": "2026-06-10T10:00:00Z",
        "source": "e2e_probe",
        "ok": True,
        "text": "看一下状态",
        "reason": "",
        "request_ms": 1800,
        "total_ms": 1720,
        "prompt_ms": 20,
        "asr_ms": 900,
        "llm_ms": 300,
        "tts_ms": 500,
        "action_ms": None,
        "asr_provider": "aliyun_funasr_realtime",
        "asr_mode": "streaming",
        "llm_model": "openai-compatible:gpt-5.5",
        "tts_provider": "aliyun_qwen_tts_realtime",
        "tts_model": "qwen3-tts-flash-realtime",
    }


def test_run_round_uses_only_new_voice_audit_events() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.posts: list[tuple[str, dict[str, Any]]] = []

        def get_json(self, path: str) -> Any:
            if path == "/api/status":
                return {"session": "IDLE"}
            if path == "/api/audit":
                if not self.posts:
                    return [{"id": "old", "event_type": "voice.turn.ok", "payload": {"source": "e2e_probe"}}]
                return [
                    {"id": "old", "event_type": "voice.turn.ok", "payload": {"source": "e2e_probe"}},
                    {
                        "id": "new",
                        "event_type": "voice.turn.command",
                        "timestamp": "2026-06-10T10:00:02Z",
                        "payload": {
                            "source": "e2e_probe",
                            "text": "向前走一点",
                            "command": "move",
                            "timing": {"asr_ms": 700, "action_ms": 500, "total_ms": 1220},
                        },
                    },
                ]
            raise AssertionError(f"unexpected GET {path}")

        def post_json(self, path: str, payload: dict[str, Any]) -> Any:
            self.posts.append((path, payload))
            return {"ok": True, "handled_locally": True, "command": "move"}

    result = voice_e2e_probe.run_round(FakeClient(), round_index=1, source="e2e_probe")

    assert result["round"] == 1
    assert result["event_id"] == "new"
    assert result["event_type"] == "voice.turn.command"
    assert result["text"] == "向前走一点"
    assert result["action_ms"] == 500
    assert result["run_once_result"] == {"ok": True, "handled_locally": True, "command": "move"}
