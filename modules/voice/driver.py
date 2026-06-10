"""Voice driver — ASR, TTS, wake word detection.

Hardware/cloud dependencies:
- ASR: provider based (Aliyun Fun-ASR/NLS, local Qwen3-ASR, Whisper, Google STT)
- TTS: edge-tts (async, free, supports Chinese zh-CN-XiaoxiaoNeural)
- Wake word: provider based (openWakeWord, Porcupine)
- Audio playback: pygame.mixer

Mock fallback mode available for CI / non-RPi environments.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import math
import os
import struct
import tempfile
import threading
import time
import wave
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Callable, Coroutine

from voice.asr import AsrProvider, AsrResult, build_asr_provider
from voice.wake_word import WakeWordProvider, build_wake_word_provider

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({"停", "停止", "急停", "stop", "halt", "emergency"})

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_ALIYUN_TTS_VOICE = "Cherry"
PROXY_ENV_VARS = (
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
)
PROXY_ENV_LOCK = threading.Lock()


class VoiceDriver:
    """Async voice driver with mock fallback."""

    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._repo_root = Path(__file__).resolve().parents[2]
        self._listening = False
        self._listen_task: asyncio.Task[None] | None = None
        self._cancel_event = asyncio.Event()
        self._recognize_lock = asyncio.Lock()
        self._voice_pause_threshold = self._resolve_float(
            os.environ.get("VOICE_PAUSE_THRESHOLD"),
            default=0.45,
            lower=0.1,
            upper=2.0,
            name="VOICE_PAUSE_THRESHOLD",
        )
        self._voice_phrase_time_limit = self._resolve_int(
            os.environ.get("VOICE_PHRASE_TIME_LIMIT"),
            default=4,
            lower=1,
            upper=30,
            name="VOICE_PHRASE_TIME_LIMIT",
        )
        self._voice_fixed_record_s = self._resolve_float(
            os.environ.get("VOICE_FIXED_RECORD_S"),
            default=0.0,
            lower=0.0,
            upper=10.0,
            name="VOICE_FIXED_RECORD_S",
        )
        self._voice_streaming_asr_enabled = self._resolve_bool(
            os.environ.get("VOICE_STREAMING_ASR_ENABLED", "false"),
            default=False,
        )
        self._voice_stream_frame_ms = self._resolve_int(
            os.environ.get("VOICE_STREAM_FRAME_MS"),
            default=20,
            lower=10,
            upper=100,
            name="VOICE_STREAM_FRAME_MS",
        )
        self._voice_stream_rms_threshold = self._resolve_int(
            os.environ.get("VOICE_STREAM_RMS_THRESHOLD"),
            default=300,
            lower=1,
            upper=20000,
            name="VOICE_STREAM_RMS_THRESHOLD",
        )
        self._voice_post_wake_no_speech_timeout_s = self._resolve_float(
            os.environ.get("VOICE_POST_WAKE_NO_SPEECH_TIMEOUT_S"),
            default=1.2,
            lower=0.2,
            upper=60.0,
            name="VOICE_POST_WAKE_NO_SPEECH_TIMEOUT_S",
        )
        self._voice_min_speech_duration_s = self._resolve_float(
            os.environ.get("VOICE_MIN_SPEECH_DURATION_S"),
            default=0.3,
            lower=0.1,
            upper=2.0,
            name="VOICE_MIN_SPEECH_DURATION_S",
        )
        self._voice_vad_stop_silence_s = self._resolve_float(
            os.environ.get("VOICE_VAD_STOP_SILENCE_S"),
            default=0.4,
            lower=0.1,
            upper=2.0,
            name="VOICE_VAD_STOP_SILENCE_S",
        )
        self._voice_stream_max_utterance_s = self._resolve_float(
            os.environ.get("VOICE_STREAM_MAX_UTTERANCE_S"),
            default=3.0,
            lower=0.5,
            upper=10.0,
            name="VOICE_STREAM_MAX_UTTERANCE_S",
        )
        self._voice_stream_pre_roll_s = self._resolve_float(
            os.environ.get("VOICE_STREAM_PRE_ROLL_S"),
            default=0.5,
            lower=0.0,
            upper=2.0,
            name="VOICE_STREAM_PRE_ROLL_S",
        )
        self._voice_energy_threshold = self._resolve_optional_int(
            os.environ.get("VOICE_ENERGY_THRESHOLD"),
            name="VOICE_ENERGY_THRESHOLD",
        )
        self._voice_dynamic_energy_threshold = self._resolve_bool(
            os.environ.get("VOICE_DYNAMIC_ENERGY_THRESHOLD", "false"),
            default=False,
        )
        self._wake_word_label = "disabled"
        self._wake_word_init_error: str | None = None
        self._wake_word_provider: WakeWordProvider | None = None
        self._input_device_index: int | None = None
        self._wake_input_device_index = self._resolve_optional_int(
            os.environ.get("VOICE_WAKE_INPUT_DEVICE_INDEX"),
            name="VOICE_WAKE_INPUT_DEVICE_INDEX",
        )
        self._input_device_name: str = "default"
        self._input_device_channels: int = 1
        self._wake_channel_mode = self._resolve_wake_channel_mode(
            os.environ.get("VOICE_WAKE_CHANNEL_MODE", "dominant")
        )
        self._wake_audio_gain = self._resolve_wake_audio_gain(
            os.environ.get("VOICE_WAKE_AUDIO_GAIN", "1.0")
        )

        self._asr_provider: AsrProvider | None = None
        self._tts_cache_dir = Path(
            os.environ.get("VOICE_TTS_CACHE_DIR", str(self._repo_root / "data" / "tts_cache"))
        )
        self._local_prompt_dir = Path(
            os.environ.get(
                "VOICE_LOCAL_PROMPT_DIR",
                str(self._repo_root / "data" / "voice_prompts"),
            )
        )
        self._wake_prompt_duration_ms = self._resolve_int(
            os.environ.get("VOICE_WAKE_PROMPT_DURATION_MS"),
            default=120,
            lower=40,
            upper=500,
            name="VOICE_WAKE_PROMPT_DURATION_MS",
        )
        self._wake_prompt_frequency_hz = self._resolve_int(
            os.environ.get("VOICE_WAKE_PROMPT_FREQUENCY_HZ"),
            default=880,
            lower=120,
            upper=2400,
            name="VOICE_WAKE_PROMPT_FREQUENCY_HZ",
        )
        self._wake_prompt_volume = self._resolve_float(
            os.environ.get("VOICE_WAKE_PROMPT_VOLUME"),
            default=0.35,
            lower=0.05,
            upper=1.0,
            name="VOICE_WAKE_PROMPT_VOLUME",
        )
        self._tts_provider = os.environ.get("VOICE_TTS_PROVIDER", "edge").strip().lower()
        self._aliyun_tts_model = os.environ.get(
            "VOICE_ALIYUN_TTS_MODEL", "qwen3-tts-flash-realtime"
        ).strip()
        self._aliyun_tts_voice = os.environ.get(
            "VOICE_ALIYUN_TTS_VOICE", DEFAULT_ALIYUN_TTS_VOICE
        ).strip()
        self._aliyun_tts_url = os.environ.get(
            "VOICE_ALIYUN_TTS_WEBSOCKET_URL",
            "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        ).strip()
        self._aliyun_tts_timeout_s = self._resolve_float(
            os.environ.get("VOICE_ALIYUN_TTS_TIMEOUT_S"),
            default=30.0,
            lower=3.0,
            upper=120.0,
            name="VOICE_ALIYUN_TTS_TIMEOUT_S",
        )
        self._aliyun_tts_volume = self._resolve_int(
            os.environ.get("VOICE_ALIYUN_TTS_VOLUME"),
            default=50,
            lower=0,
            upper=100,
            name="VOICE_ALIYUN_TTS_VOLUME",
        )
        self._aliyun_tts_disable_proxy = self._resolve_bool(
            os.environ.get("VOICE_ALIYUN_TTS_DISABLE_PROXY", "true"),
            default=True,
        )

        # Callbacks for events
        self._on_wake_word: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._on_stop_word: Callable[[], Coroutine[Any, Any, None]] | None = None

        if not mock:
            try:
                self._init_hardware()
            except (ImportError, OSError) as exc:
                logger.warning("Voice hardware not available, falling back to mock: %s", exc)
                self._mock = True
        else:
            logger.info("Voice driver initialized (mock mode)")

    @staticmethod
    def _resolve_wake_channel_mode(raw: str) -> str:
        mode = raw.strip().lower()
        if mode in {"dominant", "mix", "left", "right"}:
            return mode
        if mode:
            logger.warning("Invalid VOICE_WAKE_CHANNEL_MODE=%s, fallback to dominant", raw)
        return "dominant"

    @staticmethod
    def _resolve_wake_audio_gain(raw: str) -> float:
        try:
            gain = float(raw)
        except ValueError:
            logger.warning("Invalid VOICE_WAKE_AUDIO_GAIN=%s, fallback to 1.0", raw)
            return 1.0
        if gain <= 0:
            logger.warning("VOICE_WAKE_AUDIO_GAIN must be > 0, fallback to 1.0")
            return 1.0
        return max(0.1, min(4.0, gain))

    @staticmethod
    def _resolve_float(
        raw: str | None,
        *,
        default: float,
        lower: float,
        upper: float,
        name: str,
    ) -> float:
        if raw is None or not raw.strip():
            return default
        try:
            value = float(raw)
        except ValueError:
            logger.warning("Invalid %s=%s, fallback to %.2f", name, raw, default)
            return default
        return max(lower, min(upper, value))

    @staticmethod
    def _resolve_int(
        raw: str | None,
        *,
        default: int,
        lower: int,
        upper: int,
        name: str,
    ) -> int:
        if raw is None or not raw.strip():
            return default
        try:
            value = int(raw)
        except ValueError:
            logger.warning("Invalid %s=%s, fallback to %d", name, raw, default)
            return default
        return max(lower, min(upper, value))

    @staticmethod
    def _resolve_optional_int(raw: str | None, *, name: str) -> int | None:
        if raw is None or not raw.strip():
            return None
        try:
            value = int(raw)
        except ValueError:
            logger.warning("Invalid %s=%s, ignoring", name, raw)
            return None
        if value < 0:
            logger.warning("%s must be >= 0, ignoring", name)
            return None
        return value

    def _init_hardware(self) -> None:
        """Initialize audio hardware dependencies."""
        import speech_recognition as sr  # noqa: F401

        self._recognizer = sr.Recognizer()
        (
            self._input_device_index,
            self._input_device_name,
            self._input_device_channels,
        ) = self._resolve_input_device(sr)
        self._microphone = sr.Microphone(device_index=self._input_device_index)
        self._asr_provider = build_asr_provider(os.environ, self._recognizer)
        logger.info("ASR provider selected: %s", self._asr_provider.name)

        # Set hardware capture gain to avoid clipping.
        # seeed WM8960 defaults to max gain (63/30dB) on each driver load which causes clipping.
        # VOICE_CAPTURE_GAIN env var overrides (range 0-63, default 40 = 12.75dB).
        self._set_capture_gain()

        logger.info(
            "Voice input device selected: index=%s name=%s channels=%s wake_channel_mode=%s wake_audio_gain=%.2f",
            self._input_device_index if self._input_device_index is not None else "default",
            self._input_device_name,
            self._input_device_channels,
            self._wake_channel_mode,
            self._wake_audio_gain,
        )

        # Pre-adjust for ambient noise
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as exc:
            logger.warning("Could not adjust for ambient noise: %s", exc)
        self._recognizer.dynamic_energy_threshold = self._voice_dynamic_energy_threshold
        if self._voice_energy_threshold is not None:
            self._recognizer.energy_threshold = self._voice_energy_threshold
        logger.info(
            "Voice recognizer configured: energy_threshold=%.0f dynamic_energy_threshold=%s",
            self._recognizer.energy_threshold,
            self._recognizer.dynamic_energy_threshold,
        )

        # Initialize pygame for audio playback
        # VOICE_OUTPUT_DEVICE sets the ALSA device for SDL/pygame (e.g. "plughw:4,0" for USB speaker)
        try:
            import pygame
            output_device = os.environ.get("VOICE_OUTPUT_DEVICE", "").strip()
            if output_device:
                os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
                os.environ["AUDIODEV"] = output_device
                logger.info("Audio output device: %s", output_device)
            pygame.mixer.init()
            self._pygame = pygame
        except (ImportError, Exception) as exc:
            logger.warning("pygame not available for audio playback: %s", exc)
            self._pygame = None

        self._wake_word_provider = build_wake_word_provider(
            os.environ,
            repo_root=self._repo_root,
        )
        self._wake_word_label = self._wake_word_provider.label
        self._wake_word_init_error = self._wake_word_provider.error
        if self._wake_word_provider.available:
            logger.info(
                "Wake word provider initialized: provider=%s wake_word=%s frame_length=%s",
                self._wake_word_provider.name,
                self._wake_word_provider.label,
                self._wake_word_provider.frame_length,
            )
        else:
            logger.info("Wake word detection disabled: %s", self._wake_word_provider.error)

        logger.info("Voice driver initialized (hardware mode)")

    def _resolve_input_device(self, sr: Any) -> tuple[int | None, str, int]:
        """Resolve microphone input device from env or common name heuristics."""
        forced_index_raw = os.environ.get("VOICE_INPUT_DEVICE_INDEX", "").strip()
        forced_name = os.environ.get("VOICE_INPUT_DEVICE_NAME", "").strip().lower()

        try:
            audio = sr.Microphone.get_pyaudio().PyAudio()
            device_infos: list[dict[str, Any]] = []
            for i in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(i)
                device_infos.append({
                    "index": i,
                    "name": str(info.get("name", "")),
                    "inputs": int(info.get("maxInputChannels", 0)),
                })
            audio.terminate()
        except Exception as exc:
            logger.warning("Unable to list microphone devices: %s", exc)
            device_infos = []

        names = [d["name"] for d in device_infos]

        def pick(index: int) -> tuple[int | None, str, int]:
            if 0 <= index < len(device_infos):
                info = device_infos[index]
                if info["inputs"] > 0:
                    return index, info["name"], info["inputs"]
                logger.warning(
                    "Configured input device index=%s has no input channels (name=%s, inputs=%s); falling back",
                    index,
                    info["name"],
                    info["inputs"],
                )
            return None, "default", 1

        if forced_index_raw:
            try:
                forced_index = int(forced_index_raw)
                picked = pick(forced_index)
                if picked[0] is not None:
                    return picked
            except ValueError:
                logger.warning("Invalid VOICE_INPUT_DEVICE_INDEX=%s", forced_index_raw)

        candidates: list[str] = []
        if forced_name:
            candidates.append(forced_name)
        candidates.extend(["seeed", "respeaker", "2mic", "voicecard", "mic"])

        lowered = [n.lower() for n in names]
        for needle in candidates:
            for idx, device_name in enumerate(lowered):
                if needle and needle in device_name:
                    picked = pick(idx)
                    if picked[0] is not None:
                        return picked

        # Last fallback: first input-capable device.
        for d in device_infos:
            if d["inputs"] > 0:
                return d["index"], d["name"], d["inputs"]

        return None, "default", 1

    def _set_capture_gain(self) -> None:
        """Set ALSA audio path to avoid clipped input and noisy ReSpeaker output."""
        import subprocess

        raw = os.environ.get("VOICE_CAPTURE_GAIN", "40").strip()
        try:
            gain = max(0, min(63, int(raw)))
        except ValueError:
            gain = 40
        boost_raw = os.environ.get("VOICE_INPUT_BOOST", "1").strip()
        try:
            input_boost = max(0, min(3, int(boost_raw)))
        except ValueError:
            input_boost = 1
        high_pass = self._resolve_bool(os.environ.get("VOICE_ADC_HIGH_PASS", "true"), default=True)
        playback_volume = self._resolve_optional_volume(
            os.environ.get("VOICE_PLAYBACK_VOLUME"),
            name="VOICE_PLAYBACK_VOLUME",
        )
        output_volume = self._resolve_optional_volume(
            os.environ.get("VOICE_OUTPUT_VOLUME"),
            name="VOICE_OUTPUT_VOLUME",
        )
        output_card = os.environ.get("VOICE_OUTPUT_ALSA_CARD", "").strip()
        output_mixer = os.environ.get("VOICE_OUTPUT_MIXER", "PCM").strip()
        card = os.environ.get("VOICE_ALSA_CARD", "3").strip()

        def run_amixer(*args: str, mixer_card: str = card) -> None:
            subprocess.run(
                ["amixer", "-c", mixer_card, *args],
                capture_output=True, check=True,
            )

        try:
            run_amixer("sset", "Capture", f"{gain},{gain}")
            run_amixer("sset", "Left Input Boost Mixer LINPUT1", str(input_boost))
            run_amixer("sset", "Right Input Boost Mixer RINPUT1", str(input_boost))
            run_amixer("sset", "ADC High Pass Filter", "on" if high_pass else "off")
            if playback_volume is not None:
                run_amixer("sset", "Playback", f"{playback_volume},{playback_volume}")
            if output_volume is not None and output_card and output_mixer:
                run_amixer(
                    "sset",
                    output_mixer,
                    f"{output_volume},{output_volume}",
                    mixer_card=output_card,
                )
            db = -17.25 + gain * 0.75
            logger.info(
                "Audio path set on card %s: gain=%d (%.2fdB) input_boost=%d high_pass=%s playback_volume=%s output=%s/%s/%s",
                card,
                gain,
                db,
                input_boost,
                high_pass,
                playback_volume if playback_volume is not None else "unchanged",
                output_card or "unchanged",
                output_mixer or "unchanged",
                output_volume if output_volume is not None else "unchanged",
            )
        except Exception as exc:
            logger.warning("Could not set audio path: %s", exc)

    @staticmethod
    def _resolve_optional_volume(raw: str | None, *, name: str) -> int | None:
        if raw is None or not raw.strip():
            return None
        try:
            return max(0, min(255, int(raw)))
        except ValueError:
            logger.warning("Invalid %s=%s, ignoring", name, raw)
            return None

    @staticmethod
    def _resolve_bool(raw: str | None, *, default: bool) -> bool:
        if raw is None or not raw.strip():
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def set_on_wake_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_wake_word = callback

    def set_on_stop_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_stop_word = callback

    # ─── ASR ──────────────────────────────────────────────────

    async def recognize(
        self, language: str = "zh-CN", timeout_s: int = 10
    ) -> dict[str, Any]:
        """Recognize speech from microphone.

        Uses the configured ASR provider. `VOICE_ASR_PROVIDER=auto` prefers Aliyun
        Fun-ASR, then NLS, then local Qwen3-ASR, then Whisper, then Google STT.
        Audio capture uses speech_recognition's listen() with VAD-based sentence boundary
        detection (`VOICE_PAUSE_THRESHOLD` silence triggers end-of-utterance).
        """
        if self._mock:
            logger.info("Mock ASR: returning simulated text")
            await asyncio.sleep(0.1)
            return {"ok": True, "text": "[mock speech input]", "confidence": 0.95}

        # Avoid microphone contention with wake-word loop.
        restart_wake_loop = self._listening
        if restart_wake_loop:
            await self.listen_stop()

        try:
            async with self._recognize_lock:
                provider = self._asr_provider
                if provider is None:
                    provider = build_asr_provider(os.environ, self._recognizer)
                    self._asr_provider = provider
                if self._voice_streaming_asr_enabled and hasattr(provider, "start_stream"):
                    logger.info("Streaming ASR enabled via %s", provider.name)
                    return await self._recognize_streaming(provider, language, timeout_s)

                import speech_recognition as sr  # noqa: F401

                logger.info("Listening for speech (timeout=%ds)...", timeout_s)
                capture_start = time.monotonic()
                audio = await asyncio.to_thread(
                    self._listen_sync,
                    timeout_s,
                )
                capture_ms = _duration_ms(capture_start)

            # Check audio energy — skip ASR if too quiet (noise/silence)
            rms = self._audio_rms(audio)
            if rms < 300:
                logger.info("Audio too quiet (rms=%d), skipping ASR", rms)
                return {
                    "ok": False,
                    "error": "silence",
                    "text": "",
                    "metadata": {
                        "provider": provider.name,
                        "mode": "recorded",
                        "capture_ms": capture_ms,
                        "audio_rms": rms,
                    },
                }

            logger.info("Recognizing via %s (rms=%d)...", provider.name, rms)
            provider_start = time.monotonic()
            asr_result = await asyncio.to_thread(provider.recognize, audio, language)
            return await self._asr_result_payload(
                asr_result,
                extra_metadata={
                    "provider": provider.name,
                    "mode": "recorded",
                    "capture_ms": capture_ms,
                    "provider_ms": _duration_ms(provider_start),
                    "audio_rms": rms,
                },
            )

        except Exception as exc:
            if exc.__class__.__name__ == "WaitTimeoutError":
                logger.warning(
                    "ASR timeout: no speech detected within %ds (energy_threshold=%.0f)",
                    timeout_s,
                    self._recognizer.energy_threshold,
                )
                return {"ok": False, "error": "timeout", "text": ""}
            if exc.__class__.__name__ == "UnknownValueError":
                logger.warning(
                    "ASR unrecognized: could not understand audio (energy_threshold=%.0f)",
                    self._recognizer.energy_threshold,
                )
                return {"ok": False, "error": "unrecognized", "text": ""}
            if exc.__class__.__name__ == "RequestError":
                logger.error("ASR request error: %s", exc)
                return {"ok": False, "error": str(exc), "text": ""}
            logger.error("ASR unexpected error: %s", exc, exc_info=True)
            return {"ok": False, "error": "audio_source_error", "text": ""}
        finally:
            if restart_wake_loop:
                resumed = await self.listen_start()
                if not resumed.get("ok", False):
                    logger.warning("Failed to resume wake loop after ASR: %s", resumed)

    async def _asr_result_payload(
        self,
        asr_result: AsrResult,
        *,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self._postprocess_asr_result(asr_result)
        metadata = dict(asr_result.metadata)
        if extra_metadata:
            metadata.update(extra_metadata)

        text_lower = text.strip().lower() if isinstance(text, str) else ""

        if not text_lower:
            logger.warning("ASR returned empty text")
            payload: dict[str, Any] = {"ok": False, "error": "unrecognized", "text": ""}
            if metadata:
                payload["metadata"] = metadata
            return payload

        # Check for stop words — hardcoded, never goes through LLM
        if any(w in text_lower for w in STOP_WORDS):
            logger.warning("Stop word detected in speech: %s", text)
            if self._on_stop_word:
                await self._on_stop_word()
            payload = {"ok": True, "text": text, "is_stop_word": True}
            if metadata:
                payload["metadata"] = metadata
            return payload

        payload = {"ok": True, "text": text}
        if asr_result.confidence is not None:
            payload["confidence"] = asr_result.confidence
        if metadata:
            payload["metadata"] = metadata
        return payload

    async def _recognize_streaming(
        self,
        provider: Any,
        language: str,
        timeout_s: int,
    ) -> dict[str, Any]:
        import pyaudio

        sample_rate = int(getattr(provider, "sample_rate", 16000))
        frame_samples = max(160, int(sample_rate * self._voice_stream_frame_ms / 1000))
        frame_duration_s = frame_samples / sample_rate
        stream_channels = 2 if self._input_device_channels >= 2 else 1
        pre_roll_frames = max(1, int(self._voice_stream_pre_roll_s / frame_duration_s))
        pre_roll: deque[bytes] = deque(maxlen=pre_roll_frames)
        session = None
        elapsed_s = 0.0
        speech_s = 0.0
        silence_s = 0.0
        last_rms = 0
        peak_rms = 0
        frames_sent = 0
        vad_start_ms: int | None = None
        stream_start = time.monotonic()
        pa = pyaudio.PyAudio()
        audio_stream = None
        try:
            open_kwargs: dict[str, Any] = {
                "rate": sample_rate,
                "channels": stream_channels,
                "format": pyaudio.paInt16,
                "input": True,
                "frames_per_buffer": frame_samples,
            }
            if self._input_device_index is not None:
                open_kwargs["input_device_index"] = self._input_device_index
            audio_stream = pa.open(**open_kwargs)
            while elapsed_s < timeout_s:
                pcm = await asyncio.to_thread(
                    audio_stream.read,
                    frame_samples,
                    exception_on_overflow=False,
                )
                mono_pcm = self._mono_pcm_frame(pcm, frame_samples, stream_channels)
                rms = self._pcm_rms(mono_pcm)
                last_rms = rms
                peak_rms = max(peak_rms, rms)
                voiced = rms >= self._voice_stream_rms_threshold

                if session is None:
                    pre_roll.append(mono_pcm)
                    if voiced:
                        vad_start_ms = int(elapsed_s * 1000)
                        session = provider.start_stream(language)
                        for frame in pre_roll:
                            session.send_pcm(frame)
                            frames_sent += 1
                        speech_s = frame_duration_s
                        silence_s = 0.0
                    elif elapsed_s >= self._voice_post_wake_no_speech_timeout_s:
                        logger.info("Streaming ASR timeout before speech start (rms=%d)", rms)
                        return {"ok": False, "error": "timeout", "text": ""}
                else:
                    session.send_pcm(mono_pcm)
                    frames_sent += 1
                    speech_s += frame_duration_s
                    silence_s = 0.0 if voiced else silence_s + frame_duration_s
                    if (
                        speech_s >= self._voice_min_speech_duration_s
                        and silence_s >= self._voice_vad_stop_silence_s
                    ):
                        break
                    if speech_s >= self._voice_stream_max_utterance_s:
                        break
                elapsed_s += frame_duration_s

            if session is None:
                logger.info("Streaming ASR timed out without speech (rms=%d)", last_rms)
                return {"ok": False, "error": "timeout", "text": ""}
            return await self._asr_result_payload(
                session.finish(),
                extra_metadata={
                    "provider": provider.name,
                    "mode": "streaming",
                    "stream_ms": _duration_ms(stream_start),
                    "vad_start_ms": vad_start_ms,
                    "speech_ms": int(speech_s * 1000),
                    "silence_ms": int(silence_s * 1000),
                    "frames_sent": frames_sent,
                    "last_rms": last_rms,
                    "peak_rms": peak_rms,
                },
            )
        finally:
            if audio_stream:
                audio_stream.close()
            pa.terminate()

    @staticmethod
    def _mono_pcm_frame(pcm: bytes, frame_samples: int, channels: int) -> bytes:
        if channels <= 1:
            return pcm
        raw = struct.unpack_from(f"<{frame_samples * channels}h", pcm)
        mono = [
            int(sum(raw[(i * channels) + ch] for ch in range(channels)) / channels)
            for i in range(frame_samples)
        ]
        return struct.pack(f"<{frame_samples}h", *mono)

    @staticmethod
    def _pcm_rms(pcm: bytes) -> int:
        if len(pcm) < 2:
            return 0
        n_samples = len(pcm) // 2
        samples = struct.unpack(f"<{n_samples}h", pcm)
        sum_sq = sum(s * s for s in samples)
        return int((sum_sq / n_samples) ** 0.5)

    @staticmethod
    def _audio_rms(audio: Any) -> int:
        """Compute RMS energy of captured audio. Low RMS = silence/noise."""
        import struct
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        if len(raw) < 2:
            return 0
        n_samples = len(raw) // 2
        samples = struct.unpack(f"<{n_samples}h", raw)
        sum_sq = sum(s * s for s in samples)
        return int((sum_sq / n_samples) ** 0.5)

    def _postprocess_asr_result(self, result: AsrResult) -> str:
        text = result.text.strip()
        if result.metadata.get("audio_seconds", 1) < 0.5 and text:
            logger.warning(
                "ASR hallucination filtered (audio too short: %.1fs): '%s'",
                result.metadata["audio_seconds"],
                text,
            )
            return ""
        if text and self._is_hallucination(text):
            logger.warning("ASR hallucination filtered: '%s'", text)
            return ""
        return text

    @staticmethod
    def _is_hallucination(text: str) -> bool:
        """Detect common ASR hallucination patterns."""
        s = text.strip()
        if not s:
            return False
        # Single repeated character: "啊啊啊啊" or "......"
        if len(set(s.replace(" ", ""))) <= 2:
            return True
        # Common ASR hallucination phrases generated on silence/noise.
        hallucination_phrases = [
            "谢谢观看", "感谢收看", "字幕", "订阅", "请订阅",
            "thank you", "thanks for watching", "subscribe",
            "字幕由", "字幕提供", "请不吝点赞", "欢迎订阅",
            "有什么需要我帮忙的吗", "需要我帮忙吗", "我能帮你什么",
        ]
        s_lower = s.lower()
        for phrase in hallucination_phrases:
            if phrase in s_lower:
                return True
        return False

    def _listen_sync(self, timeout_s: int) -> Any:
        """Blocking mic capture with VAD-based sentence boundary detection.

        speech_recognition's listen() uses energy-based VAD:
        - Waits up to `timeout` seconds for speech to begin
        - Once speech detected, records until `VOICE_PAUSE_THRESHOLD` of silence
        - `VOICE_PHRASE_TIME_LIMIT` caps maximum recording duration
        """
        with self._microphone as source:
            self._recognizer.pause_threshold = self._voice_pause_threshold
            non_speaking_duration = getattr(
                self._recognizer,
                "non_speaking_duration",
                self._recognizer.pause_threshold,
            )
            self._recognizer.non_speaking_duration = min(
                non_speaking_duration,
                self._recognizer.pause_threshold,
            )
            if self._voice_fixed_record_s > 0:
                return self._recognizer.record(source, duration=self._voice_fixed_record_s)
            return self._recognizer.listen(
                source,
                timeout=timeout_s,
                phrase_time_limit=self._voice_phrase_time_limit,
            )

    # ─── TTS ──────────────────────────────────────────────────

    async def play_prompt(self, prompt: str = "wake") -> dict[str, Any]:
        """Play a local prompt sound without cloud TTS."""
        start = time.monotonic()
        prompt_name = self._normalize_prompt_name(prompt)
        if self._mock:
            await asyncio.sleep(self._wake_prompt_duration_ms / 1000)
            return {
                "ok": True,
                "prompt": prompt_name,
                "duration_ms": _duration_ms(start),
                "local": True,
            }

        try:
            prompt_path = self._local_prompt_path(prompt_name)
            if prompt_name == "wake":
                self._ensure_wake_prompt(prompt_path)
            elif not prompt_path.exists():
                raise RuntimeError(f"Local voice prompt not found: {prompt_name}")

            if self._pygame and self._pygame.mixer.get_init():
                await asyncio.to_thread(self._play_audio, str(prompt_path), False)

            return {
                "ok": True,
                "prompt": prompt_name,
                "duration_ms": _duration_ms(start),
                "local": True,
            }
        except Exception as exc:
            logger.error("Local prompt error: %s", exc)
            return {"ok": False, "prompt": prompt_name, "error": str(exc)}

    async def synthesize(
        self, text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%"
    ) -> dict[str, Any]:
        """Synthesize and play text using the configured TTS provider."""
        if self._mock:
            logger.info("Mock TTS: '%s'", text)
            await asyncio.sleep(0.1)
            return {"ok": True, "duration_ms": 100}

        try:
            start = time.monotonic()
            provider = self._normalized_tts_provider()
            resolved_voice = self._resolve_tts_voice(voice, provider)
            cached_path = self._tts_cache_path(
                text=text,
                voice=resolved_voice,
                rate=rate,
                provider=provider,
            )

            if cached_path.exists() and cached_path.stat().st_size > 0:
                if self._pygame and self._pygame.mixer.get_init():
                    await asyncio.to_thread(self._play_audio, str(cached_path))
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return {"ok": True, "duration_ms": elapsed_ms, "cached": True}

            if provider == "aliyun_qwen_tts_realtime":
                metadata = await asyncio.to_thread(
                    self._synthesize_aliyun_qwen_tts_realtime,
                    text,
                    resolved_voice,
                    rate,
                    cached_path,
                )
            else:
                metadata = await self._synthesize_edge_tts(
                    text,
                    resolved_voice,
                    rate,
                    cached_path,
                )

            if self._pygame and self._pygame.mixer.get_init():
                await asyncio.to_thread(self._play_audio, str(cached_path))

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {"ok": True, "duration_ms": elapsed_ms, **metadata}

        except Exception as exc:
            logger.error("TTS error: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _normalized_tts_provider(self) -> str:
        raw_provider = getattr(self, "_tts_provider", "edge")
        if raw_provider in {
            "aliyun",
            "aliyun_qwen",
            "aliyun_qwen_tts",
            "aliyun_qwen_tts_realtime",
            "qwen_tts_realtime",
        }:
            return "aliyun_qwen_tts_realtime"
        return "edge"

    def _resolve_tts_voice(self, voice: str, provider: str) -> str:
        if provider != "aliyun_qwen_tts_realtime":
            return voice
        stripped = voice.strip()
        if stripped and not stripped.startswith("zh-") and not stripped.endswith("Neural"):
            return stripped
        return self._aliyun_tts_voice or DEFAULT_ALIYUN_TTS_VOICE

    async def _synthesize_edge_tts(
        self,
        text: str,
        voice: str,
        rate: str,
        cached_path: Path,
    ) -> dict[str, Any]:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    tmp.write(chunk["data"])

        try:
            self._store_tts_cache(tmp_path, cached_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return {"provider": "edge"}

    def _synthesize_aliyun_qwen_tts_realtime(
        self,
        text: str,
        voice: str,
        rate: str,
        cached_path: Path,
    ) -> dict[str, Any]:
        import dashscope
        from dashscope.audio.qwen_tts_realtime import (
            AudioFormat,
            QwenTtsRealtime,
            QwenTtsRealtimeCallback,
        )

        api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Aliyun Qwen TTS")
        dashscope.api_key = api_key

        class Callback(QwenTtsRealtimeCallback):
            def __init__(self) -> None:
                self.done = threading.Event()
                self.chunks: list[bytes] = []
                self.error: str | None = None
                self.first_audio_at: float | None = None

            def on_event(self, response: Any) -> None:
                event_type = response.get("type") if isinstance(response, dict) else None
                if event_type == "response.audio.delta":
                    if self.first_audio_at is None:
                        self.first_audio_at = time.monotonic()
                    self.chunks.append(base64.b64decode(str(response["delta"])))
                elif event_type == "error":
                    self.error = json.dumps(response, ensure_ascii=False)
                    self.done.set()
                elif event_type == "session.finished":
                    self.done.set()

            def on_close(self, close_status_code: Any, close_msg: Any) -> None:
                if not self.done.is_set() and close_status_code not in (None, 1000):
                    self.error = f"closed: {close_status_code} {close_msg}"
                    self.done.set()

        callback = Callback()
        start = time.monotonic()
        synthesizer = QwenTtsRealtime(
            model=self._aliyun_tts_model,
            callback=callback,
            url=self._aliyun_tts_url,
        )
        proxy_scope = (
            self._without_proxy_env()
            if getattr(self, "_aliyun_tts_disable_proxy", True)
            else nullcontext()
        )
        with proxy_scope:
            try:
                synthesizer.connect()
                synthesizer.update_session(
                    voice=voice,
                    response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                    mode="server_commit",
                    speech_rate=self._parse_speech_rate(rate),
                    volume=self._aliyun_tts_volume,
                )
                synthesizer.append_text(text)
                synthesizer.finish()
                if not callback.done.wait(self._aliyun_tts_timeout_s):
                    raise TimeoutError("Aliyun Qwen TTS timed out")
                if callback.error:
                    raise RuntimeError(callback.error)
                pcm = b"".join(callback.chunks)
                if not pcm:
                    raise RuntimeError("Aliyun Qwen TTS returned empty audio")
                self._store_pcm_wav_cache(pcm, cached_path, sample_rate=24000)
                first_audio_ms = (
                    int((callback.first_audio_at - start) * 1000)
                    if callback.first_audio_at is not None
                    else None
                )
                metadata: dict[str, Any] = {
                    "provider": "aliyun_qwen_tts_realtime",
                    "model": self._aliyun_tts_model,
                    "voice": voice,
                    "audio_bytes": len(pcm),
                }
                if first_audio_ms is not None:
                    metadata["first_audio_ms"] = first_audio_ms
                first_package_delay = synthesizer.get_first_audio_delay()
                if first_package_delay is not None:
                    metadata["first_package_delay_ms"] = first_package_delay
                session_id = synthesizer.get_session_id()
                if session_id:
                    metadata["session_id"] = session_id
                return metadata
            finally:
                try:
                    synthesizer.close()
                except Exception:
                    pass

    @staticmethod
    @contextmanager
    def _without_proxy_env() -> Iterator[None]:
        with PROXY_ENV_LOCK:
            previous = {key: os.environ.get(key) for key in PROXY_ENV_VARS}
            try:
                for key in PROXY_ENV_VARS:
                    os.environ.pop(key, None)
                yield
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def _store_pcm_wav_cache(self, pcm: bytes, cache_path: Path, *, sample_rate: int) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp_cache = cache_path.with_suffix(".tmp")
            with wave.open(str(temp_cache), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(pcm)
            temp_cache.replace(cache_path)
        except OSError as exc:
            logger.warning("Could not store TTS cache: %s", exc)

    @staticmethod
    def _parse_speech_rate(rate: str) -> float:
        normalized = rate.strip().replace("%", "")
        try:
            percent = float(normalized)
        except ValueError:
            return 1.0
        return max(0.5, min(2.0, 1.0 + percent / 100.0))

    def _tts_cache_path(
        self,
        *,
        text: str,
        voice: str,
        rate: str,
        provider: str = "edge",
    ) -> Path:
        key = "\0".join([provider, text, voice, rate]).encode("utf-8")
        digest = hashlib.sha256(key).hexdigest()[:24]
        suffix = ".wav" if provider == "aliyun_qwen_tts_realtime" else ".mp3"
        return self._tts_cache_dir / f"{digest}{suffix}"

    def _store_tts_cache(self, source_path: str, cache_path: Path) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp_cache = cache_path.with_suffix(".tmp")
            temp_cache.write_bytes(Path(source_path).read_bytes())
            temp_cache.replace(cache_path)
        except OSError as exc:
            logger.warning("Could not store TTS cache: %s", exc)

    def _play_audio(self, path: str, boost: bool = True) -> None:
        """Play an audio file synchronously using pygame."""
        if not self._pygame:
            return
        play_path = self._prepare_playback_audio(path) if boost else path
        self._pygame.mixer.music.load(play_path)
        self._pygame.mixer.music.play()
        while self._pygame.mixer.music.get_busy():
            time.sleep(0.05)

    def _local_prompt_path(self, prompt: str) -> Path:
        return self._local_prompt_dir / f"{prompt}.wav"

    @staticmethod
    def _normalize_prompt_name(prompt: str) -> str:
        normalized = prompt.strip().lower()
        if not normalized:
            return "wake"
        sanitized = "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"})
        return sanitized or "wake"

    def _ensure_wake_prompt(self, path: Path) -> None:
        if path.exists() and path.stat().st_size > 0:
            return
        self._write_tone_wav(
            path,
            frequency_hz=self._wake_prompt_frequency_hz,
            duration_ms=self._wake_prompt_duration_ms,
            volume=self._wake_prompt_volume,
        )

    @staticmethod
    def _write_tone_wav(
        path: Path,
        *,
        frequency_hz: int,
        duration_ms: int,
        volume: float,
        sample_rate: int = 24000,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame_count = max(1, int(sample_rate * duration_ms / 1000))
        amplitude = int(32767 * volume)
        frames = bytearray()
        for index in range(frame_count):
            sample = int(amplitude * math.sin(2 * math.pi * frequency_hz * index / sample_rate))
            frames.extend(struct.pack("<h", sample))
        temp_path = path.with_suffix(".tmp")
        with wave.open(str(temp_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(frames))
        temp_path.replace(path)

    def _prepare_playback_audio(self, path: str) -> str:
        boosted = Path(f"{path}.boost.mp3")
        source = Path(path)
        try:
            if (
                boosted.exists()
                and boosted.stat().st_size > 0
                and boosted.stat().st_mtime >= source.stat().st_mtime
            ):
                return str(boosted)

            import subprocess

            subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), "-filter:a", "volume=8dB", str(boosted)],
                capture_output=True,
                timeout=10,
            )
            if boosted.exists() and boosted.stat().st_size > 0:
                return str(boosted)
        except Exception:
            return path
        return path

    # ─── Wake Word Detection ──────────────────────────────────

    async def listen_start(self) -> dict[str, Any]:
        """Start wake word detection loop."""
        if self._listen_task and self._listen_task.done():
            self._listen_task = None

        if self._listening:
            return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

        if self._listen_task and not self._listen_task.done():
            return {
                "ok": False,
                "error": "wake_loop_stopping",
                "listening": False,
                "wake_word": self._wake_word_label,
            }

        if self._mock:
            self._listening = True
            self._cancel_event.clear()
            logger.info("Mock wake word detection started")
            return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

        provider = self._wake_word_provider
        if not provider or not provider.available:
            logger.warning("Wake word provider unavailable: %s", self._wake_word_init_error)
            return {
                "ok": False,
                "error": "wake_word_not_available",
                "provider": provider.name if provider else "unknown",
                "init_error": self._wake_word_init_error,
                "listening": False,
                "wake_word": self._wake_word_label,
            }

        self._listening = True
        self._cancel_event.clear()
        self._listen_task = asyncio.create_task(self._wake_word_loop())
        return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

    async def listen_stop(self) -> dict[str, Any]:
        """Stop wake word detection loop."""
        self._listening = False
        self._cancel_event.set()

        if self._listen_task and not self._listen_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(self._listen_task), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Wake word loop did not stop within timeout")
                return {"ok": False, "error": "wake_loop_stop_timeout"}

        self._listen_task = None

        logger.info("Wake word detection stopped")
        return {"ok": True}

    async def _wake_word_loop(self) -> None:
        """Background loop for wake word detection."""
        try:
            import struct

            provider = self._wake_word_provider
            if not provider or not provider.available:
                return

            pa = None
            audio_stream = None
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                stream_channels = 1
                if self._input_device_channels >= 2:
                    # 2-mic arrays are common on RPi hats; capture 2ch and downmix to mono.
                    stream_channels = 2
                open_kwargs: dict[str, Any] = {
                    "rate": provider.sample_rate,
                    "channels": stream_channels,
                    "format": pyaudio.paInt16,
                    "input": True,
                    "frames_per_buffer": provider.frame_length,
                }
                wake_input_index = self._wake_input_device_index
                if wake_input_index is None:
                    wake_input_index = self._input_device_index
                if wake_input_index is not None:
                    open_kwargs["input_device_index"] = wake_input_index

                audio_stream = pa.open(
                    **open_kwargs
                )

                logger.info(
                    "Wake word detection active (input_index=%s, stream_channels=%s, channel_mode=%s, gain=%.2f)",
                    wake_input_index if wake_input_index is not None else "default",
                    stream_channels,
                    self._wake_channel_mode,
                    self._wake_audio_gain,
                )
                while self._listening:
                    if self._cancel_event.is_set():
                        break
                    pcm = await asyncio.to_thread(
                        audio_stream.read,
                        provider.frame_length, exception_on_overflow=False,
                    )
                    if stream_channels == 1:
                        pcm_unpacked = struct.unpack_from(
                            "h" * provider.frame_length, pcm
                        )
                    else:
                        raw = struct.unpack_from(
                            "h" * (provider.frame_length * stream_channels), pcm
                        )
                        if self._wake_channel_mode == "mix":
                            # Downmix interleaved multi-channel samples to mono.
                            pcm_unpacked = tuple(
                                int(
                                    sum(raw[(i * stream_channels) + ch] for ch in range(stream_channels))
                                    / stream_channels
                                )
                                for i in range(provider.frame_length)
                            )
                        else:
                            selected_channel = 0
                            if self._wake_channel_mode == "right" and stream_channels >= 2:
                                selected_channel = 1
                            elif self._wake_channel_mode == "dominant" and stream_channels >= 2:
                                channel_levels = [0] * stream_channels
                                for i in range(provider.frame_length):
                                    base = i * stream_channels
                                    for ch in range(stream_channels):
                                        channel_levels[ch] += abs(raw[base + ch])
                                selected_channel = max(
                                    range(stream_channels),
                                    key=lambda idx: channel_levels[idx],
                                )
                            pcm_unpacked = tuple(
                                raw[(i * stream_channels) + selected_channel]
                                for i in range(provider.frame_length)
                            )

                    if self._wake_audio_gain != 1.0:
                        pcm_unpacked = tuple(
                            max(-32768, min(32767, int(sample * self._wake_audio_gain)))
                            for sample in pcm_unpacked
                        )
                    detection = provider.process(pcm_unpacked)

                    if detection.detected:
                        logger.info(
                            "Wake word detected: provider=%s label=%s score=%.3f",
                            provider.name,
                            detection.label,
                            detection.score,
                        )
                        if self._on_wake_word:
                            await self._on_wake_word()

                    # Yield to event loop
                    await asyncio.sleep(0)

            finally:
                if audio_stream:
                    audio_stream.close()
                if pa:
                    pa.terminate()

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._listening = False
            logger.error("Wake word loop error: %s", exc)

    # ─── Emergency Stop ───────────────────────────────────────

    async def stop(self) -> None:
        """Emergency stop: stop all voice operations."""
        await self.listen_stop()
        if not self._mock and self._pygame and self._pygame.mixer.get_init():
            try:
                self._pygame.mixer.music.stop()
            except Exception:
                pass
        logger.info("Voice driver emergency stopped")

    def cleanup(self) -> None:
        """Release hardware resources."""
        self._listening = False
        if not self._mock:
            if self._wake_word_provider:
                try:
                    self._wake_word_provider.close()
                except Exception:
                    pass
            if hasattr(self, "_pygame") and self._pygame:
                try:
                    self._pygame.mixer.quit()
                except Exception:
                    pass


def _duration_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
