"""Voice driver — ASR, TTS, wake word detection.

Hardware/cloud dependencies:
- ASR: speech_recognition + Google STT (cloud)
- TTS: edge-tts (async, free, supports Chinese zh-CN-XiaoxiaoNeural)
- Wake word: pvporcupine (Picovoice, requires PICOVOICE_ACCESS_KEY)
- Audio playback: pygame.mixer

Mock fallback mode available for CI / non-RPi environments.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({"停", "停止", "急停", "stop", "halt", "emergency"})

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class VoiceDriver:
    """Async voice driver with mock fallback."""

    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._listening = False
        self._listen_task: asyncio.Task[None] | None = None
        self._cancel_event = asyncio.Event()
        self._recognize_lock = asyncio.Lock()
        self._wake_word_label = "disabled"
        self._wake_word_init_error: str | None = None
        self._input_device_index: int | None = None
        self._input_device_name: str = "default"
        self._input_device_channels: int = 1
        self._wake_channel_mode = self._resolve_wake_channel_mode(
            os.environ.get("VOICE_WAKE_CHANNEL_MODE", "dominant")
        )
        self._wake_audio_gain = self._resolve_wake_audio_gain(
            os.environ.get("VOICE_WAKE_AUDIO_GAIN", "1.0")
        )

        # Whisper ASR config (local LAN service)
        whisper_url = os.environ.get("WHISPER_URL", "").strip().rstrip("/")
        self._whisper_url = f"{whisper_url}/transcribe" if whisper_url else ""
        if self._whisper_url:
            logger.info("Whisper ASR endpoint: %s", self._whisper_url)

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

    def _init_hardware(self) -> None:
        """Initialize audio hardware dependencies."""
        import speech_recognition as sr  # noqa: F401

        self._recognizer = sr.Recognizer()
        self._input_device_index, self._input_device_name, self._input_device_channels = self._resolve_input_device(sr)
        self._microphone = sr.Microphone(device_index=self._input_device_index)

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

        # Initialize Porcupine wake word engine
        self._porcupine = None
        self._wake_word_init_error = None
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "")
        if access_key:
            try:
                import pvporcupine
                repo_root = Path(__file__).resolve().parents[2]

                keyword_path = os.environ.get("PICOVOICE_KEYWORD_PATH", "").strip()
                model_path = os.environ.get("PICOVOICE_MODEL_PATH", "").strip()
                builtin_keyword = os.environ.get("PICOVOICE_BUILTIN_KEYWORD", "picovoice").strip()
                sensitivity_raw = os.environ.get("PICOVOICE_SENSITIVITY", "0.55").strip()

                try:
                    sensitivity = float(sensitivity_raw)
                except ValueError:
                    sensitivity = 0.55
                sensitivity = max(0.0, min(1.0, sensitivity))

                if not keyword_path:
                    legacy_keyword_candidates = [
                        repo_root / "legacy" / "src" / "wake_words" / "kk_zh_raspberry-pi_v3_0_0.ppn",
                        repo_root / "legacy" / "wake_words" / "kk_zh_raspberry-pi_v3_0_0.ppn",
                    ]
                    for candidate in legacy_keyword_candidates:
                        if candidate.exists():
                            keyword_path = str(candidate)
                            break

                if not model_path:
                    # If caller specifies a custom keyword file, first try matching model in same folder.
                    if keyword_path:
                        keyword_parent = Path(keyword_path).expanduser().resolve().parent
                        local_model_candidates = [
                            keyword_parent / "porcupine_params_zh.pv",
                            keyword_parent / "porcupine_params.pv",
                        ]
                        local_model_candidates.extend(sorted(keyword_parent.glob("porcupine_params*.pv")))
                        for candidate in local_model_candidates:
                            if candidate.exists():
                                model_path = str(candidate)
                                break
                    else:
                        # Backward-compatibility for legacy v3 assets.
                        legacy_model_candidates = [
                            repo_root / "legacy" / "src" / "wake_words" / "porcupine_params_zh.pv",
                            repo_root / "legacy" / "wake_words" / "porcupine_params_zh.pv",
                            repo_root / "legacy" / "models" / "porcupine" / "porcupine_params_zh.pv",
                        ]
                        for candidate in legacy_model_candidates:
                            if candidate.exists():
                                model_path = str(candidate)
                                break

                def try_init_porcupine(kwargs: dict[str, Any], label: str, source: str) -> bool:
                    try:
                        self._porcupine = pvporcupine.create(**kwargs)
                        self._wake_word_label = label
                        self._wake_word_init_error = None
                        logger.info(
                            "Porcupine wake word engine initialized (wake_word=%s, sensitivity=%.2f, source=%s)",
                            self._wake_word_label,
                            sensitivity,
                            source,
                        )
                        return True
                    except Exception as exc:
                        self._porcupine = None
                        self._wake_word_init_error = str(exc)
                        logger.warning("Porcupine init failed (source=%s): %s", source, exc)
                        return False

                base_kwargs: dict[str, Any] = {"access_key": access_key}
                if model_path:
                    model_path_resolved = str(Path(model_path).expanduser().resolve())
                    if Path(model_path_resolved).exists():
                        base_kwargs["model_path"] = model_path_resolved
                    else:
                        logger.warning("PICOVOICE_MODEL_PATH does not exist: %s", model_path_resolved)

                used_keyword_path = False
                create_kwargs = dict(base_kwargs)
                create_kwargs["sensitivities"] = [sensitivity]

                if keyword_path:
                    keyword_path_resolved = str(Path(keyword_path).expanduser().resolve())
                    if Path(keyword_path_resolved).exists():
                        create_kwargs["keyword_paths"] = [keyword_path_resolved]
                        used_keyword_path = True
                        if not try_init_porcupine(
                            create_kwargs,
                            Path(keyword_path_resolved).name,
                            "keyword_path",
                        ):
                            # Legacy .ppn may be incompatible with newer pvporcupine.
                            # Fall back to a builtin keyword to keep wake loop usable.
                            fallback_kwargs: dict[str, Any] = {
                                "access_key": access_key,
                                "keywords": [builtin_keyword],
                                "sensitivities": [sensitivity],
                            }
                            if try_init_porcupine(
                                fallback_kwargs,
                                builtin_keyword,
                                "builtin_fallback_after_keyword_error",
                            ):
                                logger.warning(
                                    "Custom wake word file is incompatible or invalid; "
                                    "falling back to builtin keyword '%s'.", builtin_keyword
                                )
                    else:
                        logger.warning("PICOVOICE_KEYWORD_PATH does not exist: %s", keyword_path_resolved)

                if self._porcupine is None and not used_keyword_path:
                    create_kwargs = dict(base_kwargs)
                    create_kwargs["keywords"] = [builtin_keyword]
                    create_kwargs["sensitivities"] = [sensitivity]
                    try_init_porcupine(create_kwargs, builtin_keyword, "builtin_keyword")
            except (ImportError, Exception) as exc:
                self._wake_word_init_error = str(exc)
                logger.warning("Porcupine not available: %s", exc)
        else:
            self._wake_word_init_error = "PICOVOICE_ACCESS_KEY not set"
            logger.info("PICOVOICE_ACCESS_KEY not set, wake word detection disabled")

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
        """Set ALSA capture gain to prevent clipping. seeed WM8960 resets to max on every load."""
        import subprocess
        raw = os.environ.get("VOICE_CAPTURE_GAIN", "40").strip()
        try:
            gain = max(0, min(63, int(raw)))
        except ValueError:
            gain = 40
        card = os.environ.get("VOICE_ALSA_CARD", "3").strip()
        try:
            subprocess.run(
                ["amixer", "-c", card, "sset", "Capture", f"{gain},{gain}"],
                capture_output=True, check=True,
            )
            db = -17.25 + gain * 0.75
            logger.info("Capture gain set to %d (%.2fdB) on card %s", gain, db, card)
        except Exception as exc:
            logger.warning("Could not set capture gain: %s", exc)

    def set_on_wake_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_wake_word = callback

    def set_on_stop_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_stop_word = callback

    # ─── ASR ──────────────────────────────────────────────────

    async def recognize(
        self, language: str = "zh-CN", timeout_s: int = 10
    ) -> dict[str, Any]:
        """Recognize speech from microphone.

        Uses local Whisper service if WHISPER_URL is set, otherwise falls back to Google STT.
        Audio capture uses speech_recognition's listen() with VAD-based sentence boundary
        detection (pause_threshold=0.8s silence triggers end-of-utterance).
        """
        if self._mock:
            logger.info("Mock ASR: returning simulated text")
            await asyncio.sleep(0.1)
            return {"ok": True, "text": "[mock speech input]", "confidence": 0.95}

        import speech_recognition as sr

        # Avoid microphone contention with wake-word loop.
        restart_wake_loop = self._listening
        if restart_wake_loop:
            await self.listen_stop()

        try:
            async with self._recognize_lock:
                logger.info("Listening for speech (timeout=%ds)...", timeout_s)
                audio = await asyncio.to_thread(
                    self._listen_sync,
                    timeout_s,
                )

            # Check audio energy — skip ASR if too quiet (noise/silence)
            rms = self._audio_rms(audio)
            if rms < 300:
                logger.info("Audio too quiet (rms=%d), skipping ASR", rms)
                return {"ok": False, "error": "silence", "text": ""}

            # Choose ASR backend
            if self._whisper_url:
                logger.info("Recognizing via Whisper (rms=%d)...", rms)
                text = await asyncio.to_thread(
                    self._recognize_whisper,
                    audio,
                    language,
                )
            else:
                logger.info("Recognizing via Google STT (rms=%d)...", rms)
                text = await asyncio.to_thread(
                    self._recognizer.recognize_google,
                    audio,
                    language=language,
                )

            text_lower = text.strip().lower() if isinstance(text, str) else ""

            if not text_lower:
                logger.warning("ASR returned empty text")
                return {"ok": False, "error": "unrecognized", "text": ""}

            # Check for stop words — hardcoded, never goes through LLM
            if any(w in text_lower for w in STOP_WORDS):
                logger.warning("Stop word detected in speech: %s", text)
                if self._on_stop_word:
                    await self._on_stop_word()
                return {"ok": True, "text": text, "is_stop_word": True}

            return {"ok": True, "text": text, "confidence": 0.9}

        except sr.WaitTimeoutError:
            logger.warning("ASR timeout: no speech detected within %ds (energy_threshold=%.0f)", timeout_s, self._recognizer.energy_threshold)
            return {"ok": False, "error": "timeout", "text": ""}
        except sr.UnknownValueError:
            logger.warning("ASR unrecognized: could not understand audio (energy_threshold=%.0f)", self._recognizer.energy_threshold)
            return {"ok": False, "error": "unrecognized", "text": ""}
        except sr.RequestError as exc:
            logger.error("ASR request error: %s", exc)
            return {"ok": False, "error": str(exc), "text": ""}
        except Exception as exc:
            logger.error("ASR unexpected error: %s", exc, exc_info=True)
            return {"ok": False, "error": "audio_source_error", "text": ""}
        finally:
            if restart_wake_loop:
                resumed = await self.listen_start()
                if not resumed.get("ok", False):
                    logger.warning("Failed to resume wake loop after ASR: %s", resumed)

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

    def _recognize_whisper(self, audio: Any, language: str) -> str:
        """Send captured audio to local Whisper HTTP service for transcription."""
        import io
        import json
        import urllib.request

        # Convert SpeechRecognition AudioData to WAV bytes
        wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)

        # Build multipart form data
        boundary = "----WhisperBoundary"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
        body.write(b"Content-Type: audio/wav\r\n\r\n")
        body.write(wav_data)
        body.write(f"\r\n--{boundary}--\r\n".encode())
        body_bytes = body.getvalue()

        # Map language codes: zh-CN -> zh
        lang = language.split("-")[0] if "-" in language else language
        url = f"{self._whisper_url}?task=transcribe&language={lang}"

        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        # Bypass proxy for local Whisper service
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        with opener.open(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())

        text = result.get("text", "").strip()
        audio_seconds = result.get("audio_seconds", 0)
        logger.info("Whisper result: '%s' (audio_seconds=%.1f)", text, audio_seconds)

        # Filter Whisper hallucinations:
        # - very short audio (<0.5s) with text is usually noise
        # - repeated characters/phrases are hallucination artifacts
        if text and audio_seconds < 0.5:
            logger.warning("Whisper hallucination filtered (audio too short: %.1fs): '%s'", audio_seconds, text)
            return ""
        if text and self._is_hallucination(text):
            logger.warning("Whisper hallucination filtered: '%s'", text)
            return ""

        return text

    @staticmethod
    def _is_hallucination(text: str) -> bool:
        """Detect common Whisper hallucination patterns."""
        s = text.strip()
        if not s:
            return False
        # Single repeated character: "啊啊啊啊" or "......"
        if len(set(s.replace(" ", ""))) <= 2:
            return True
        # Common hallucination phrases (Whisper generates these on silence)
        hallucination_phrases = [
            "谢谢观看", "感谢收看", "字幕", "订阅", "请订阅",
            "thank you", "thanks for watching", "subscribe",
            "字幕由", "字幕提供", "请不吝点赞", "欢迎订阅",
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
        - Once speech detected, records until `pause_threshold` (0.8s) of silence
        - `phrase_time_limit` caps maximum recording duration
        """
        with self._microphone as source:
            return self._recognizer.listen(
                source,
                timeout=timeout_s,
                phrase_time_limit=30,
            )

    # ─── TTS ──────────────────────────────────────────────────

    async def synthesize(
        self, text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%"
    ) -> dict[str, Any]:
        """Synthesize and play text using Edge TTS."""
        if self._mock:
            logger.info("Mock TTS: '%s'", text)
            await asyncio.sleep(0.1)
            return {"ok": True, "duration_ms": 100}

        try:
            import edge_tts

            start = time.monotonic()

            communicate = edge_tts.Communicate(text, voice, rate=rate)

            # Write to temp file and play
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        tmp.write(chunk["data"])

            # Play audio
            if self._pygame and self._pygame.mixer.get_init():
                await asyncio.to_thread(self._play_audio, tmp_path)

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            return {"ok": True, "duration_ms": elapsed_ms}

        except Exception as exc:
            logger.error("TTS error: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _play_audio(self, path: str) -> None:
        """Play an audio file synchronously using pygame."""
        if not self._pygame:
            return
        # Boost volume via ffmpeg (+6dB ≈ 2x loudness)
        boosted = path + ".boost.mp3"
        try:
            import subprocess
            subprocess.run(
                ["ffmpeg", "-y", "-i", path, "-filter:a", "volume=8dB", boosted],
                capture_output=True, timeout=10,
            )
            play_path = boosted if os.path.exists(boosted) else path
        except Exception:
            play_path = path
        self._pygame.mixer.music.load(play_path)
        self._pygame.mixer.music.play()
        while self._pygame.mixer.music.get_busy():
            time.sleep(0.05)
        try:
            os.unlink(boosted)
        except OSError:
            pass

    # ─── Wake Word Detection ──────────────────────────────────

    async def listen_start(self) -> dict[str, Any]:
        """Start wake word detection loop."""
        if self._listening:
            return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

        self._listening = True
        self._cancel_event.clear()

        if self._mock:
            logger.info("Mock wake word detection started")
            return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

        if not self._porcupine:
            logger.warning("Porcupine not initialized, wake word detection unavailable")
            return {
                "ok": False,
                "error": "porcupine_not_available",
                "init_error": self._wake_word_init_error,
                "listening": False,
                "wake_word": self._wake_word_label,
            }

        self._listen_task = asyncio.create_task(self._wake_word_loop())
        return {"ok": True, "listening": True, "wake_word": self._wake_word_label}

    async def listen_stop(self) -> dict[str, Any]:
        """Stop wake word detection loop."""
        self._listening = False
        self._cancel_event.set()

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        logger.info("Wake word detection stopped")
        return {"ok": True}

    async def _wake_word_loop(self) -> None:
        """Background loop for wake word detection using Porcupine."""
        try:
            import pvporcupine
            import struct

            pa = None
            audio_stream = None
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                stream_channels = 1
                if self._input_device_channels >= 2:
                    # 2-mic arrays are common on RPi hats; capture 2ch and downmix to mono for Porcupine.
                    stream_channels = 2
                open_kwargs: dict[str, Any] = {
                    "rate": self._porcupine.sample_rate,
                    "channels": stream_channels,
                    "format": pyaudio.paInt16,
                    "input": True,
                    "frames_per_buffer": self._porcupine.frame_length,
                }
                if self._input_device_index is not None:
                    open_kwargs["input_device_index"] = self._input_device_index

                audio_stream = pa.open(
                    **open_kwargs
                )

                logger.info(
                    "Wake word detection active (input_index=%s, stream_channels=%s, channel_mode=%s, gain=%.2f)",
                    self._input_device_index if self._input_device_index is not None else "default",
                    stream_channels,
                    self._wake_channel_mode,
                    self._wake_audio_gain,
                )
                while self._listening:
                    if self._cancel_event.is_set():
                        break
                    pcm = await asyncio.to_thread(
                        audio_stream.read,
                        self._porcupine.frame_length, exception_on_overflow=False,
                    )
                    if stream_channels == 1:
                        pcm_unpacked = struct.unpack_from(
                            "h" * self._porcupine.frame_length, pcm
                        )
                    else:
                        raw = struct.unpack_from(
                            "h" * (self._porcupine.frame_length * stream_channels), pcm
                        )
                        if self._wake_channel_mode == "mix":
                            # Downmix interleaved multi-channel samples to mono.
                            pcm_unpacked = tuple(
                                int(
                                    sum(raw[(i * stream_channels) + ch] for ch in range(stream_channels))
                                    / stream_channels
                                )
                                for i in range(self._porcupine.frame_length)
                            )
                        else:
                            selected_channel = 0
                            if self._wake_channel_mode == "right" and stream_channels >= 2:
                                selected_channel = 1
                            elif self._wake_channel_mode == "dominant" and stream_channels >= 2:
                                channel_levels = [0] * stream_channels
                                for i in range(self._porcupine.frame_length):
                                    base = i * stream_channels
                                    for ch in range(stream_channels):
                                        channel_levels[ch] += abs(raw[base + ch])
                                selected_channel = max(
                                    range(stream_channels),
                                    key=lambda idx: channel_levels[idx],
                                )
                            pcm_unpacked = tuple(
                                raw[(i * stream_channels) + selected_channel]
                                for i in range(self._porcupine.frame_length)
                            )

                    if self._wake_audio_gain != 1.0:
                        pcm_unpacked = tuple(
                            max(-32768, min(32767, int(sample * self._wake_audio_gain)))
                            for sample in pcm_unpacked
                        )
                    keyword_index = self._porcupine.process(pcm_unpacked)

                    if keyword_index >= 0:
                        logger.info("Wake word detected!")
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
            if hasattr(self, "_porcupine") and self._porcupine:
                try:
                    self._porcupine.delete()
                except Exception:
                    pass
            if hasattr(self, "_pygame") and self._pygame:
                try:
                    self._pygame.mixer.quit()
                except Exception:
                    pass
