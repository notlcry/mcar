"""Tests for wake word provider selection and inference."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from voice.wake_word import (
    DisabledWakeWordProvider,
    OpenWakeWordProvider,
    WakeWordDetection,
    build_wake_word_provider,
)


def test_build_wake_word_provider_can_disable_detection() -> None:
    provider = build_wake_word_provider({"VOICE_WAKE_PROVIDER": "none"})

    assert isinstance(provider, DisabledWakeWordProvider)
    assert provider.available is False
    assert provider.error == "wake word disabled"


def test_openwakeword_provider_detects_score_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, Any] = {}

    class FakeModel:
        def __init__(self, **kwargs: Any) -> None:
            created.update(kwargs)

        def predict(self, audio: Any) -> dict[str, float]:
            created["audio_dtype"] = str(audio.dtype)
            created["audio_len"] = int(audio.shape[0])
            return {"hey_jarvis": 0.72}

    fake_model_module = types.SimpleNamespace(Model=FakeModel)
    monkeypatch.setitem(sys.modules, "openwakeword.model", fake_model_module)

    provider = OpenWakeWordProvider(
        wakeword_models=["hey_jarvis"],
        threshold=0.6,
        inference_framework="onnx",
    )

    result = provider.process([0] * 1280)

    assert result == WakeWordDetection(
        detected=True,
        label="hey_jarvis",
        score=0.72,
        scores={"hey_jarvis": 0.72},
    )
    assert created["wakeword_models"] == ["hey_jarvis"]
    assert created["inference_framework"] == "onnx"
    assert created["audio_dtype"] == "int16"
    assert created["audio_len"] == 1280


def test_openwakeword_provider_uses_env_model_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeModel:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def predict(self, audio: Any) -> dict[str, float]:
            return {"hey_mycroft": 0.1}

    fake_model_module = types.SimpleNamespace(Model=FakeModel)
    monkeypatch.setitem(sys.modules, "openwakeword.model", fake_model_module)

    provider = build_wake_word_provider(
        {
            "VOICE_WAKE_PROVIDER": "openwakeword",
            "OPENWAKEWORD_MODEL_NAME": "hey_mycroft",
            "OPENWAKEWORD_THRESHOLD": "0.4",
            "OPENWAKEWORD_INFERENCE_FRAMEWORK": "onnx",
        },
        repo_root=Path("/tmp/mcar"),
    )

    assert isinstance(provider, OpenWakeWordProvider)
    assert provider.available is True
    assert provider.label == "hey_mycroft"
    assert provider.threshold == 0.4


def test_openwakeword_provider_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "openwakeword.model", raising=False)

    provider = build_wake_word_provider(
        {
            "VOICE_WAKE_PROVIDER": "openwakeword",
            "OPENWAKEWORD_MODEL_NAME": "hey_mycroft",
        }
    )

    assert provider.available is False
    assert provider.error is not None
    assert "openWakeWord" in provider.error
