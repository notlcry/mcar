"""Tests for the Voice module capabilities (mock mode)."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import struct
import sys
import types
import wave
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice.asr import (
    AliyunNlsAsrProvider,
    AliyunFunAsrRealtimeProvider,
    AsrResult,
    GoogleAsrProvider,
    Qwen3AsrLocalProvider,
    WhisperAsrProvider,
    build_asr_provider,
)
from voice.driver import VoiceDriver
from voice.module import VoiceModule


@pytest.fixture
def voice_driver() -> VoiceDriver:
    """Create a VoiceDriver in mock mode."""
    return VoiceDriver(mock=True)


@pytest.fixture
def voice_module() -> VoiceModule:
    """Create a VoiceModule without starting IPC."""
    m = VoiceModule.__new__(VoiceModule)
    m._driver = VoiceDriver(mock=True)
    return m


class TestVoiceModuleManifest:
    def test_manifest(self, voice_module: VoiceModule) -> None:
        manifest = voice_module.manifest()
        assert manifest["module_id"] == "voice"
        assert "tool.voice.recognize" in manifest["capabilities"]
        assert "tool.voice.synthesize" in manifest["capabilities"]
        assert "tool.voice.play_prompt" in manifest["capabilities"]
        assert "tool.voice.listen_start" in manifest["capabilities"]
        assert "tool.voice.listen_stop" in manifest["capabilities"]

    def test_capabilities(self, voice_module: VoiceModule) -> None:
        caps = voice_module.capabilities()
        assert len(caps) == 5
        cap_ids = [c["capability_id"] for c in caps]
        assert "tool.voice.recognize" in cap_ids
        assert "tool.voice.synthesize" in cap_ids
        assert "tool.voice.play_prompt" in cap_ids
        assert "tool.voice.listen_start" in cap_ids
        assert "tool.voice.listen_stop" in cap_ids


class TestVoiceDriverASR:
    @pytest.mark.asyncio
    async def test_recognize_mock(self, voice_driver: VoiceDriver) -> None:
        result = await voice_driver.recognize(language="zh-CN", timeout_s=5)
        assert result["ok"] is True
        assert result["text"] == "[mock speech input]"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_asr_filters_assistant_prompt_hallucination(
        self,
        voice_driver: VoiceDriver,
    ) -> None:
        result = await voice_driver._asr_result_payload(AsrResult(text="有什么需要我帮忙的吗？"))

        assert result == {"ok": False, "error": "unrecognized", "text": ""}

    @pytest.mark.asyncio
    async def test_asr_payload_merges_provider_and_capture_metadata(
        self,
        voice_driver: VoiceDriver,
    ) -> None:
        result = await voice_driver._asr_result_payload(
            AsrResult(text="向前走", metadata={"request_id": "req-1"}),
            extra_metadata={"provider": "aliyun_funasr_realtime", "mode": "recorded"},
        )

        assert result == {
            "ok": True,
            "text": "向前走",
            "metadata": {
                "request_id": "req-1",
                "provider": "aliyun_funasr_realtime",
                "mode": "recorded",
            },
        }

    def test_auto_provider_prefers_aliyun_funasr_when_configured(self) -> None:
        provider = build_asr_provider(
            {
                "DASHSCOPE_API_KEY": "dashscope-key",
                "ALIYUN_NLS_APPKEY": "app-key",
                "ALIYUN_NLS_TOKEN": "token",
            },
            google_recognizer=object(),
        )

        assert isinstance(provider, AliyunFunAsrRealtimeProvider)

    def test_aliyun_funasr_defaults_to_realtime_chunk_interval(self) -> None:
        provider = build_asr_provider(
            {"DASHSCOPE_API_KEY": "dashscope-key"},
            google_recognizer=object(),
        )

        assert isinstance(provider, AliyunFunAsrRealtimeProvider)
        assert provider.chunk_size == 3200
        assert provider.chunk_interval_s == 0.1

    def test_aliyun_funasr_uses_phrase_id_for_hotwords(self) -> None:
        provider = build_asr_provider(
            {
                "DASHSCOPE_API_KEY": "dashscope-key",
                "ALIYUN_FUNASR_PHRASE_ID": "phrase-123",
            },
            google_recognizer=object(),
        )

        assert isinstance(provider, AliyunFunAsrRealtimeProvider)
        assert provider.phrase_id == "phrase-123"

    def test_auto_provider_prefers_aliyun_when_configured(self) -> None:
        provider = build_asr_provider(
            {
                "ALIYUN_NLS_APPKEY": "app-key",
                "ALIYUN_NLS_TOKEN": "token",
                "WHISPER_URL": "http://whisper.local",
            },
            google_recognizer=object(),
        )

        assert isinstance(provider, AliyunNlsAsrProvider)

    def test_auto_provider_requires_complete_aliyun_config(self) -> None:
        with pytest.raises(ValueError, match="ALIYUN_NLS_TOKEN is required"):
            build_asr_provider(
                {"ALIYUN_NLS_APPKEY": "app-key"},
                google_recognizer=object(),
            )

    def test_explicit_whisper_provider_uses_whisper_url(self) -> None:
        provider = build_asr_provider(
            {
                "VOICE_ASR_PROVIDER": "whisper",
                "WHISPER_URL": "http://whisper.local",
            },
            google_recognizer=object(),
        )

        assert isinstance(provider, WhisperAsrProvider)
        assert provider.url == "http://whisper.local/transcribe"

    def test_explicit_qwen3_provider_uses_local_url(self) -> None:
        provider = build_asr_provider(
            {
                "VOICE_ASR_PROVIDER": "qwen3_asr_local",
                "QWEN3_ASR_URL": "http://mac.local:8765",
            },
            google_recognizer=object(),
        )

        assert isinstance(provider, Qwen3AsrLocalProvider)
        assert provider.url == "http://mac.local:8765/transcribe"

    def test_qwen3_provider_posts_wav_to_local_service(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def read(self) -> bytes:
                payload = {"text": "向前走", "language": "Chinese", "confidence": 0.77}
                return json.dumps(payload).encode()

        class FakeOpener:
            def open(self, req: Any, timeout: int) -> FakeResponse:
                captured["url"] = req.full_url
                captured["body"] = req.data
                captured["content_type"] = req.headers["Content-type"]
                captured["timeout"] = timeout
                return FakeResponse()

        monkeypatch.setattr(
            "urllib.request.build_opener",
            lambda *args: FakeOpener(),
        )
        provider = Qwen3AsrLocalProvider(
            url="http://mac.local:8765/transcribe",
            timeout_s=12,
        )

        class FakeAudio:
            def get_wav_data(self, convert_rate: int, convert_width: int) -> bytes:
                assert convert_rate == 16000
                assert convert_width == 2
                return b"RIFF-wav-data"

        result = provider.recognize(FakeAudio(), "zh-CN")

        assert result == AsrResult(
            text="向前走",
            confidence=0.77,
            metadata={"language": "Chinese"},
        )
        assert captured["url"] == "http://mac.local:8765/transcribe"
        assert captured["timeout"] == 12
        assert b'filename="audio.wav"' in captured["body"]
        assert b'name="language"' in captured["body"]
        assert b"Chinese" in captured["body"]

    def test_explicit_google_provider_uses_google_recognizer(self) -> None:
        recognizer = object()
        provider = build_asr_provider(
            {"VOICE_ASR_PROVIDER": "google"},
            google_recognizer=recognizer,
        )

        assert isinstance(provider, GoogleAsrProvider)
        assert provider.recognizer is recognizer

    def test_listen_sync_uses_env_vad_timing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("VOICE_PAUSE_THRESHOLD", "0.45")
        monkeypatch.setenv("VOICE_PHRASE_TIME_LIMIT", "6")
        driver = VoiceDriver(mock=True)
        captured: dict[str, Any] = {}

        class FakeRecognizer:
            pause_threshold = 0.8

            def listen(
                self,
                source: Any,
                *,
                timeout: int,
                phrase_time_limit: int,
            ) -> str:
                captured["source"] = source
                captured["timeout"] = timeout
                captured["phrase_time_limit"] = phrase_time_limit
                captured["pause_threshold"] = self.pause_threshold
                return "audio"

        class FakeMicrophone:
            def __enter__(self) -> str:
                return "source"

            def __exit__(self, *args: Any) -> None:
                pass

        driver._recognizer = FakeRecognizer()
        driver._microphone = FakeMicrophone()

        assert driver._listen_sync(timeout_s=3) == "audio"
        assert captured == {
            "source": "source",
            "timeout": 3,
            "phrase_time_limit": 6,
            "pause_threshold": 0.45,
        }

    def test_listen_sync_keeps_non_speaking_duration_within_pause_threshold(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("VOICE_PAUSE_THRESHOLD", "0.45")
        driver = VoiceDriver(mock=True)
        captured: dict[str, Any] = {}

        class FakeRecognizer:
            pause_threshold = 0.8
            non_speaking_duration = 0.5

            def listen(
                self,
                source: Any,
                *,
                timeout: int,
                phrase_time_limit: int,
            ) -> str:
                captured["pause_threshold"] = self.pause_threshold
                captured["non_speaking_duration"] = self.non_speaking_duration
                return "audio"

        class FakeMicrophone:
            def __enter__(self) -> str:
                return "source"

            def __exit__(self, *args: Any) -> None:
                pass

        driver._recognizer = FakeRecognizer()
        driver._microphone = FakeMicrophone()

        assert driver._listen_sync(timeout_s=3) == "audio"
        assert captured == {
            "pause_threshold": 0.45,
            "non_speaking_duration": 0.45,
        }

    def test_listen_sync_can_use_fixed_record_window(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("VOICE_FIXED_RECORD_S", "3")
        driver = VoiceDriver(mock=True)
        captured: dict[str, Any] = {}

        class FakeRecognizer:
            pause_threshold = 0.8
            non_speaking_duration = 0.5

            def record(self, source: Any, *, duration: float) -> str:
                captured["source"] = source
                captured["duration"] = duration
                return "audio"

            def listen(self, *args: Any, **kwargs: Any) -> str:
                raise AssertionError("listen should not be used with fixed recording")

        class FakeMicrophone:
            def __enter__(self) -> str:
                return "source"

            def __exit__(self, *args: Any) -> None:
                pass

        driver._recognizer = FakeRecognizer()
        driver._microphone = FakeMicrophone()

        assert driver._listen_sync(timeout_s=3) == "audio"
        assert captured == {"source": "source", "duration": 3.0}

    def test_set_capture_gain_configures_respeaker_capture_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **_: Any) -> None:
            calls.append(cmd)

        monkeypatch.setenv("VOICE_ALSA_CARD", "3")
        monkeypatch.setenv("VOICE_CAPTURE_GAIN", "25")
        monkeypatch.setenv("VOICE_INPUT_BOOST", "1")
        monkeypatch.setenv("VOICE_ADC_HIGH_PASS", "true")
        monkeypatch.setenv("VOICE_PLAYBACK_VOLUME", "180")
        monkeypatch.setenv("VOICE_OUTPUT_ALSA_CARD", "4")
        monkeypatch.setenv("VOICE_OUTPUT_MIXER", "PCM")
        monkeypatch.setenv("VOICE_OUTPUT_VOLUME", "26")
        monkeypatch.setattr("subprocess.run", fake_run)
        driver = VoiceDriver.__new__(VoiceDriver)

        driver._set_capture_gain()

        assert calls == [
            ["amixer", "-c", "3", "sset", "Capture", "25,25"],
            ["amixer", "-c", "3", "sset", "Left Input Boost Mixer LINPUT1", "1"],
            ["amixer", "-c", "3", "sset", "Right Input Boost Mixer RINPUT1", "1"],
            ["amixer", "-c", "3", "sset", "ADC High Pass Filter", "on"],
            ["amixer", "-c", "3", "sset", "Playback", "180,180"],
            ["amixer", "-c", "4", "sset", "PCM", "26,26"],
        ]

    def test_aliyun_provider_streams_pcm_chunks_and_returns_sentence_end(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        instances: list[Any] = []

        class FakeTranscriber:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.sent: list[bytes] = []
                self.start_kwargs: dict[str, Any] = {}
                instances.append(self)

            def start(self, **kwargs: Any) -> bool:
                self.start_kwargs = kwargs
                return True

            def send_audio(self, data: bytes) -> bool:
                self.sent.append(data)
                return True

            def stop(self, timeout: int = 10) -> bool:
                message = json.dumps({"payload": {"result": "打开客厅灯", "confidence": 0.88}})
                self.kwargs["on_sentence_end"](message)
                self.kwargs["on_completed"]("{}")
                return True

        fake_nls = types.SimpleNamespace(NlsSpeechTranscriber=FakeTranscriber)
        monkeypatch.setitem(sys.modules, "nls", fake_nls)
        provider = AliyunNlsAsrProvider(
            appkey="app-key",
            token="token",
            url="wss://nls.example/ws/v1",
            chunk_size=640,
            chunk_interval_s=0,
        )

        class FakeAudio:
            def get_raw_data(self, convert_rate: int, convert_width: int) -> bytes:
                assert convert_rate == 16000
                assert convert_width == 2
                return b"0" * 1280

        result = provider.recognize(FakeAudio(), "zh-CN")

        assert result == AsrResult(text="打开客厅灯", confidence=0.88)
        assert instances[0].sent == [b"0" * 640, b"0" * 640]
        assert instances[0].start_kwargs["aformat"] == "pcm"
        assert instances[0].start_kwargs["sample_rate"] == 16000

    def test_aliyun_funasr_streams_pcm_chunks_and_returns_sentence_end(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        instances: list[Any] = []

        class FakeRecognitionResult:
            @staticmethod
            def is_sentence_end(sentence: dict[str, Any]) -> bool:
                return bool(sentence.get("sentence_end"))

        class FakeResult:
            request_id = "request-1"
            message = ""

            def get_sentence(self) -> dict[str, Any]:
                return {"text": "打开客厅灯", "sentence_end": True}

            def get_request_id(self) -> str:
                return self.request_id

            def get_usage(self, sentence: dict[str, Any]) -> dict[str, int]:
                return {"duration": 320}

        class FakeRecognition:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.sent: list[bytes] = []
                instances.append(self)

            def start(self) -> None:
                self.kwargs["callback"].on_open()

            def send_audio_frame(self, data: bytes) -> None:
                self.sent.append(data)

            def stop(self) -> None:
                self.kwargs["callback"].on_event(FakeResult())
                self.kwargs["callback"].on_complete()

            def get_last_request_id(self) -> str:
                return "request-1"

            def get_first_package_delay(self) -> int:
                return 30

            def get_last_package_delay(self) -> int:
                return 40

        class FakeRecognitionCallback:
            pass

        fake_dashscope = types.SimpleNamespace(
            api_key=None,
            base_websocket_api_url=None,
        )
        fake_asr = types.SimpleNamespace(
            Recognition=FakeRecognition,
            RecognitionCallback=FakeRecognitionCallback,
            RecognitionResult=FakeRecognitionResult,
        )
        monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)
        monkeypatch.setitem(sys.modules, "dashscope.audio", types.SimpleNamespace(asr=fake_asr))
        monkeypatch.setitem(sys.modules, "dashscope.audio.asr", fake_asr)

        provider = AliyunFunAsrRealtimeProvider(
            api_key="dashscope-key",
            websocket_url="wss://dashscope.example/api-ws/v1/inference",
            chunk_size=3200,
            chunk_interval_s=0,
        )

        class FakeAudio:
            def get_raw_data(self, convert_rate: int, convert_width: int) -> bytes:
                assert convert_rate == 16000
                assert convert_width == 2
                return b"0" * 6400

        result = provider.recognize(FakeAudio(), "zh-CN")

        assert result.text == "打开客厅灯"
        assert result.metadata["request_id"] == "request-1"
        assert result.metadata["first_package_delay_ms"] == 30
        assert instances[0].sent == [b"0" * 3200, b"0" * 3200]
        assert instances[0].kwargs["model"] == "fun-asr-realtime"
        assert instances[0].kwargs["language_hints"] == ["zh"]

    def test_aliyun_funasr_streaming_session_passes_phrase_id_and_records_partials(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        instances: list[Any] = []

        class FakeRecognitionResult:
            @staticmethod
            def is_sentence_end(sentence: dict[str, Any]) -> bool:
                return bool(sentence.get("sentence_end"))

        class FakePartialResult:
            def get_sentence(self) -> dict[str, Any]:
                return {"text": "向前", "sentence_end": False}

        class FakeFinalResult:
            def get_sentence(self) -> dict[str, Any]:
                return {"text": "向前走", "sentence_end": True}

            def get_request_id(self) -> str:
                return "request-2"

        class FakeRecognition:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.start_kwargs: dict[str, Any] = {}
                instances.append(self)

            def start(self, **kwargs: Any) -> None:
                self.start_kwargs = kwargs
                self.kwargs["callback"].on_open()

            def send_audio_frame(self, data: bytes) -> None:
                pass

            def stop(self) -> None:
                self.kwargs["callback"].on_event(FakePartialResult())
                self.kwargs["callback"].on_event(FakeFinalResult())
                self.kwargs["callback"].on_complete()

            def get_last_request_id(self) -> str:
                return "request-2"

            def get_first_package_delay(self) -> None:
                return None

            def get_last_package_delay(self) -> None:
                return None

        class FakeRecognitionCallback:
            pass

        fake_dashscope = types.SimpleNamespace(
            api_key=None,
            base_websocket_api_url=None,
        )
        fake_asr = types.SimpleNamespace(
            Recognition=FakeRecognition,
            RecognitionCallback=FakeRecognitionCallback,
            RecognitionResult=FakeRecognitionResult,
        )
        monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)
        monkeypatch.setitem(sys.modules, "dashscope.audio", types.SimpleNamespace(asr=fake_asr))
        monkeypatch.setitem(sys.modules, "dashscope.audio.asr", fake_asr)

        provider = AliyunFunAsrRealtimeProvider(
            api_key="dashscope-key",
            phrase_id="phrase-123",
        )

        session = provider.start_stream("zh-CN")
        result = session.finish()

        assert result.text == "向前走"
        assert result.metadata["partial_texts"] == ["向前"]
        assert instances[0].start_kwargs == {"phrase_id": "phrase-123"}

    def test_aliyun_funasr_streaming_session_sends_live_frames_without_sleep(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        instances: list[Any] = []

        class FakeRecognitionResult:
            @staticmethod
            def is_sentence_end(sentence: dict[str, Any]) -> bool:
                return bool(sentence.get("sentence_end"))

        class FakeResult:
            def get_sentence(self) -> dict[str, Any]:
                return {"text": "向前走", "sentence_end": True}

            def get_request_id(self) -> str:
                return "stream-request"

            def get_usage(self, sentence: dict[str, Any]) -> dict[str, int]:
                return {"duration": 120}

        class FakeRecognition:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs
                self.sent: list[bytes] = []
                instances.append(self)

            def start(self) -> None:
                self.kwargs["callback"].on_open()

            def send_audio_frame(self, data: bytes) -> None:
                self.sent.append(data)

            def stop(self) -> None:
                self.kwargs["callback"].on_event(FakeResult())
                self.kwargs["callback"].on_complete()

            def get_last_request_id(self) -> str:
                return "stream-request"

            def get_first_package_delay(self) -> int:
                return 25

            def get_last_package_delay(self) -> int:
                return 35

        class FakeRecognitionCallback:
            pass

        fake_dashscope = types.SimpleNamespace(
            api_key=None,
            base_websocket_api_url=None,
        )
        fake_asr = types.SimpleNamespace(
            Recognition=FakeRecognition,
            RecognitionCallback=FakeRecognitionCallback,
            RecognitionResult=FakeRecognitionResult,
        )
        monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)
        monkeypatch.setitem(sys.modules, "dashscope.audio", types.SimpleNamespace(asr=fake_asr))
        monkeypatch.setitem(sys.modules, "dashscope.audio.asr", fake_asr)

        sleeps: list[float] = []
        monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))
        provider = AliyunFunAsrRealtimeProvider(
            api_key="dashscope-key",
            chunk_interval_s=0.1,
        )

        session = provider.start_stream("zh-CN")
        session.send_pcm(b"frame-1")
        session.send_pcm(b"frame-2")
        result = session.finish()

        assert result.text == "向前走"
        assert result.metadata["request_id"] == "stream-request"
        assert instances[0].sent == [b"frame-1", b"frame-2"]
        assert sleeps == []

    @pytest.mark.asyncio
    async def test_recognize_streaming_uses_vad_endpoint_and_live_frames(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        speech_frame = struct.pack("<320h", *([1200] * 320))
        silence_frame = struct.pack("<320h", *([0] * 320))
        frames = [silence_frame] + [speech_frame] * 20 + [silence_frame] * 20

        class FakeAudioStream:
            def read(self, frame_count: int, exception_on_overflow: bool = False) -> bytes:
                assert frame_count == 320
                if frames:
                    return frames.pop(0)
                return silence_frame

            def close(self) -> None:
                pass

        class FakePyAudio:
            paInt16 = 8

            def PyAudio(self) -> "FakePyAudio":
                return self

            def open(self, **kwargs: Any) -> FakeAudioStream:
                assert kwargs["rate"] == 16000
                assert kwargs["channels"] == 1
                assert kwargs["frames_per_buffer"] == 320
                return FakeAudioStream()

            def terminate(self) -> None:
                pass

        class FakeSession:
            def __init__(self) -> None:
                self.sent: list[bytes] = []

            def send_pcm(self, pcm: bytes) -> None:
                self.sent.append(pcm)

            def finish(self) -> AsrResult:
                return AsrResult(text="向前走", metadata={"streaming": True})

        class FakeStreamingProvider:
            name = "fake_streaming"
            sample_rate = 16000

            def __init__(self) -> None:
                self.session = FakeSession()

            def start_stream(self, language: str) -> FakeSession:
                assert language == "zh-CN"
                return self.session

        fake_provider = FakeStreamingProvider()
        monkeypatch.setitem(sys.modules, "pyaudio", FakePyAudio())
        driver = VoiceDriver.__new__(VoiceDriver)
        driver._mock = False
        driver._listening = False
        driver._recognize_lock = asyncio.Lock()
        driver._asr_provider = fake_provider
        driver._input_device_index = None
        driver._input_device_channels = 1
        driver._voice_streaming_asr_enabled = True
        driver._voice_stream_frame_ms = 20
        driver._voice_stream_rms_threshold = 300
        driver._voice_post_wake_no_speech_timeout_s = 1.2
        driver._voice_min_speech_duration_s = 0.3
        driver._voice_vad_stop_silence_s = 0.35
        driver._voice_stream_max_utterance_s = 3.0
        driver._voice_stream_pre_roll_s = 0.1

        result = await driver.recognize(language="zh-CN", timeout_s=3)

        assert result["ok"] is True
        assert result["text"] == "向前走"
        assert result["metadata"]["streaming"] is True
        assert result["metadata"]["provider"] == "fake_streaming"
        assert result["metadata"]["mode"] == "streaming"
        assert result["metadata"]["frames_sent"] > 0
        assert result["metadata"]["vad_start_ms"] == 20
        assert result["metadata"]["peak_rms"] == 1200
        assert fake_provider.session.sent[0] == silence_frame
        assert speech_frame in fake_provider.session.sent

    def test_streaming_no_speech_timeout_accepts_long_window(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("VOICE_POST_WAKE_NO_SPEECH_TIMEOUT_S", "30")

        driver = VoiceDriver(mock=True)

        assert driver._voice_post_wake_no_speech_timeout_s == 30


class TestVoiceDriverTTS:
    @pytest.mark.asyncio
    async def test_synthesize_mock(self, voice_driver: VoiceDriver) -> None:
        result = await voice_driver.synthesize(text="Hello world")
        assert result["ok"] is True
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_synthesize_custom_voice(self, voice_driver: VoiceDriver) -> None:
        result = await voice_driver.synthesize(
            text="Test", voice="en-US-JennyNeural", rate="+10%"
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_play_prompt_generates_local_wake_tone(
        self,
        tmp_path: Path,
    ) -> None:
        driver = VoiceDriver.__new__(VoiceDriver)
        driver._mock = False
        driver._pygame = None
        driver._local_prompt_dir = tmp_path
        driver._wake_prompt_duration_ms = 80
        driver._wake_prompt_frequency_hz = 880
        driver._wake_prompt_volume = 0.3

        result = await driver.play_prompt("wake")

        assert result["ok"] is True
        assert result["prompt"] == "wake"
        prompt_path = tmp_path / "wake.wav"
        assert prompt_path.exists()
        with wave.open(str(prompt_path), "rb") as wav:
            assert wav.getframerate() == 24000
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getnframes() == 1920

    @pytest.mark.asyncio
    async def test_synthesize_reuses_cached_audio(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[tuple[str, str, str]] = []
        played: list[str] = []

        class FakeCommunicate:
            def __init__(self, text: str, voice: str, rate: str) -> None:
                calls.append((text, voice, rate))

            async def stream(self) -> Any:
                yield {"type": "audio", "data": b"cached mp3 data"}

        class FakeMusic:
            def load(self, path: str) -> None:
                played.append(path)

            def play(self) -> None:
                pass

            def get_busy(self) -> bool:
                return False

        class FakeMixer:
            music = FakeMusic()

            def get_init(self) -> bool:
                return True

        fake_edge_tts = types.SimpleNamespace(Communicate=FakeCommunicate)
        monkeypatch.setitem(sys.modules, "edge_tts", fake_edge_tts)
        driver = VoiceDriver.__new__(VoiceDriver)
        driver._mock = False
        driver._pygame = types.SimpleNamespace(mixer=FakeMixer())
        driver._tts_cache_dir = tmp_path

        first = await driver.synthesize("收到。")
        second = await driver.synthesize("收到。")

        assert first["ok"] is True
        assert second["ok"] is True
        assert calls == [("收到。", "zh-CN-XiaoxiaoNeural", "+0%")]
        assert len(played) == 2
        assert played[0] == played[1]

    @pytest.mark.asyncio
    async def test_synthesize_uses_aliyun_qwen_tts_realtime(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: dict[str, Any] = {}
        pcm = struct.pack("<hhhh", 1, -1, 2, -2)

        class FakeCallback:
            pass

        class FakeFormat:
            PCM_24000HZ_MONO_16BIT = object()

        class FakeQwenTtsRealtime:
            def __init__(self, *, model: str, callback: Any, url: str) -> None:
                calls["model"] = model
                calls["url"] = url
                self.callback = callback

            def connect(self) -> None:
                calls["connected"] = True

            def update_session(self, **kwargs: Any) -> None:
                calls["session"] = kwargs

            def append_text(self, text: str) -> None:
                calls["text"] = text

            def finish(self) -> None:
                self.callback.on_event({
                    "type": "response.audio.delta",
                    "delta": base64.b64encode(pcm).decode(),
                })
                self.callback.on_event({"type": "session.finished"})

            def get_first_audio_delay(self) -> float:
                return 123.0

            def get_session_id(self) -> str:
                return "sess-test"

            def close(self) -> None:
                calls["closed"] = True

        fake_dashscope = types.SimpleNamespace(api_key=None)
        fake_tts_module = types.SimpleNamespace(
            AudioFormat=FakeFormat,
            QwenTtsRealtime=FakeQwenTtsRealtime,
            QwenTtsRealtimeCallback=FakeCallback,
        )
        monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)
        monkeypatch.setitem(sys.modules, "dashscope.audio", types.SimpleNamespace())
        monkeypatch.setitem(
            sys.modules,
            "dashscope.audio.qwen_tts_realtime",
            fake_tts_module,
        )
        monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")

        driver = VoiceDriver.__new__(VoiceDriver)
        driver._mock = False
        driver._pygame = None
        driver._tts_cache_dir = tmp_path
        driver._tts_provider = "aliyun_qwen_tts_realtime"
        driver._aliyun_tts_model = "qwen3-tts-flash-realtime"
        driver._aliyun_tts_voice = "Cherry"
        driver._aliyun_tts_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        driver._aliyun_tts_timeout_s = 3.0
        driver._aliyun_tts_volume = 50

        result = await driver.synthesize("测试完成。", voice="zh-CN-XiaoxiaoNeural")

        assert result["ok"] is True
        assert result["provider"] == "aliyun_qwen_tts_realtime"
        assert result["model"] == "qwen3-tts-flash-realtime"
        assert result["voice"] == "Cherry"
        assert result["audio_bytes"] == len(pcm)
        assert result["first_package_delay_ms"] == 123.0
        assert calls["session"]["voice"] == "Cherry"
        assert calls["session"]["speech_rate"] == 1.0
        cached_files = list(tmp_path.glob("*.wav"))
        assert len(cached_files) == 1
        with wave.open(str(cached_files[0]), "rb") as wav:
            assert wav.getframerate() == 24000
            assert wav.readframes(4) == pcm

    @pytest.mark.asyncio
    async def test_aliyun_qwen_tts_realtime_ignores_service_proxy_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: dict[str, Any] = {}
        pcm = struct.pack("<hh", 1, -1)

        class FakeCallback:
            pass

        class FakeFormat:
            PCM_24000HZ_MONO_16BIT = object()

        class FakeQwenTtsRealtime:
            def __init__(self, *, model: str, callback: Any, url: str) -> None:
                self.callback = callback

            def connect(self) -> None:
                calls["proxy_during_connect"] = {
                    key: os.environ.get(key)
                    for key in (
                        "http_proxy",
                        "https_proxy",
                        "all_proxy",
                        "HTTP_PROXY",
                        "HTTPS_PROXY",
                        "ALL_PROXY",
                    )
                }

            def update_session(self, **kwargs: Any) -> None:
                pass

            def append_text(self, text: str) -> None:
                pass

            def finish(self) -> None:
                self.callback.on_event({
                    "type": "response.audio.delta",
                    "delta": base64.b64encode(pcm).decode(),
                })
                self.callback.on_event({"type": "session.finished"})

            def get_first_audio_delay(self) -> None:
                return None

            def get_session_id(self) -> None:
                return None

            def close(self) -> None:
                pass

        fake_tts_module = types.SimpleNamespace(
            AudioFormat=FakeFormat,
            QwenTtsRealtime=FakeQwenTtsRealtime,
            QwenTtsRealtimeCallback=FakeCallback,
        )
        monkeypatch.setitem(sys.modules, "dashscope", types.SimpleNamespace(api_key=None))
        monkeypatch.setitem(sys.modules, "dashscope.audio", types.SimpleNamespace())
        monkeypatch.setitem(
            sys.modules,
            "dashscope.audio.qwen_tts_realtime",
            fake_tts_module,
        )
        monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:7890")
        monkeypatch.setenv("https_proxy", "http://127.0.0.1:7890")
        monkeypatch.setenv("all_proxy", "socks5://127.0.0.1:7890")
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7890")
        monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
        monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:7890")

        driver = VoiceDriver.__new__(VoiceDriver)
        driver._mock = False
        driver._pygame = None
        driver._tts_cache_dir = tmp_path
        driver._tts_provider = "aliyun_qwen_tts_realtime"
        driver._aliyun_tts_model = "qwen3-tts-flash-realtime"
        driver._aliyun_tts_voice = "Cherry"
        driver._aliyun_tts_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        driver._aliyun_tts_timeout_s = 3.0
        driver._aliyun_tts_volume = 50

        result = await driver.synthesize("测试代理。")

        assert result["ok"] is True
        assert set(calls["proxy_during_connect"].values()) == {None}
        assert os.environ["http_proxy"] == "http://127.0.0.1:7890"
        assert os.environ["https_proxy"] == "http://127.0.0.1:7890"
        assert os.environ["all_proxy"] == "socks5://127.0.0.1:7890"
        assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:7890"
        assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:7890"
        assert os.environ["ALL_PROXY"] == "socks5://127.0.0.1:7890"

    def test_prepare_playback_audio_reuses_boosted_cache(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source = tmp_path / "voice.mp3"
        source.write_bytes(b"mp3")
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **_: Any) -> None:
            calls.append(cmd)
            Path(cmd[-1]).write_bytes(b"boosted mp3")

        monkeypatch.setattr("subprocess.run", fake_run)
        driver = VoiceDriver.__new__(VoiceDriver)

        first = driver._prepare_playback_audio(str(source))
        second = driver._prepare_playback_audio(str(source))

        assert first == second
        assert first.endswith(".boost.mp3")
        assert len(calls) == 1


class TestVoiceDriverWakeWord:
    def test_wake_loop_can_use_separate_input_device_index(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("VOICE_WAKE_INPUT_DEVICE_INDEX", "4")
        driver = VoiceDriver(mock=True)

        assert driver._wake_input_device_index == 4
        assert driver._input_device_index is None

    @pytest.mark.asyncio
    async def test_listen_start_stop(self, voice_driver: VoiceDriver) -> None:
        result = await voice_driver.listen_start()
        assert result["ok"] is True
        assert result["listening"] is True

        result = await voice_driver.listen_stop()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_listen_start_idempotent(self, voice_driver: VoiceDriver) -> None:
        await voice_driver.listen_start()
        result = await voice_driver.listen_start()
        assert result["ok"] is True
        assert result["listening"] is True
        await voice_driver.listen_stop()

    @pytest.mark.asyncio
    async def test_listen_stop_waits_without_cancelling_wake_task(self) -> None:
        driver = VoiceDriver.__new__(VoiceDriver)
        driver._listening = True
        driver._cancel_event = asyncio.Event()
        driver._wake_word_label = "hey_jarvis"

        async def fake_wake_loop() -> None:
            await driver._cancel_event.wait()

        task = asyncio.create_task(fake_wake_loop())
        driver._listen_task = task

        result = await driver.listen_stop()

        assert result == {"ok": True}
        assert task.done()
        assert not task.cancelled()
        assert driver._listen_task is None


class TestVoiceModuleInvoke:
    @pytest.mark.asyncio
    async def test_invoke_recognize(self, voice_module: VoiceModule) -> None:
        result = await voice_module.invoke(
            "tool.voice.recognize", {"language": "zh-CN"}, {}
        )
        assert result["ok"] is True
        assert "text" in result

    @pytest.mark.asyncio
    async def test_invoke_synthesize(self, voice_module: VoiceModule) -> None:
        result = await voice_module.invoke(
            "tool.voice.synthesize", {"text": "Hello"}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_play_prompt(self, voice_module: VoiceModule) -> None:
        result = await voice_module.invoke("tool.voice.play_prompt", {"prompt": "wake"}, {})
        assert result["ok"] is True
        assert result["prompt"] == "wake"

    @pytest.mark.asyncio
    async def test_invoke_listen_start(self, voice_module: VoiceModule) -> None:
        result = await voice_module.invoke("tool.voice.listen_start", {}, {})
        assert result["ok"] is True
        # Clean up
        await voice_module.invoke("tool.voice.listen_stop", {}, {})

    @pytest.mark.asyncio
    async def test_invoke_listen_stop(self, voice_module: VoiceModule) -> None:
        result = await voice_module.invoke("tool.voice.listen_stop", {}, {})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_unknown(self, voice_module: VoiceModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await voice_module.invoke("tool.voice.nonexistent", {}, {})


class TestVoiceCapabilitiesSpec:
    """Validate capabilities.json configuration for voice module."""

    def test_recognize_has_retry_policy(self, voice_module: VoiceModule) -> None:
        caps = voice_module.capabilities()
        recognize = next(c for c in caps if c["capability_id"] == "tool.voice.recognize")
        retry = recognize["constraints"]["retry_policy"]
        assert "E_TIMEOUT" in retry["retriable_errors"]
        assert "E_DEPENDENCY_NETWORK" in retry["retriable_errors"]
        assert retry["max_retries"] >= 1
        assert retry["backoff_ms"] > 0

    def test_synthesize_has_retry_policy(self, voice_module: VoiceModule) -> None:
        caps = voice_module.capabilities()
        synth = next(c for c in caps if c["capability_id"] == "tool.voice.synthesize")
        retry = synth["constraints"]["retry_policy"]
        assert "E_TIMEOUT" in retry["retriable_errors"]
        assert retry["max_retries"] >= 1

    def test_synthesize_has_concurrency_limit(self, voice_module: VoiceModule) -> None:
        caps = voice_module.capabilities()
        synth = next(c for c in caps if c["capability_id"] == "tool.voice.synthesize")
        concurrency = synth["constraints"]["concurrency"]
        assert concurrency["max_in_flight"] == 1


class TestVoiceDriverEmergencyStop:
    @pytest.mark.asyncio
    async def test_stop(self, voice_driver: VoiceDriver) -> None:
        await voice_driver.listen_start()
        await voice_driver.stop()
        assert voice_driver._listening is False
