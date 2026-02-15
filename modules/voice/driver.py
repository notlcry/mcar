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
import io
import logging
import os
import tempfile
import time
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

    def _init_hardware(self) -> None:
        """Initialize audio hardware dependencies."""
        import speech_recognition as sr  # noqa: F401

        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()

        # Pre-adjust for ambient noise
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as exc:
            logger.warning("Could not adjust for ambient noise: %s", exc)

        # Initialize pygame for audio playback
        try:
            import pygame
            pygame.mixer.init()
            self._pygame = pygame
        except (ImportError, Exception) as exc:
            logger.warning("pygame not available for audio playback: %s", exc)
            self._pygame = None

        # Initialize Porcupine wake word engine
        self._porcupine = None
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "")
        if access_key:
            try:
                import pvporcupine
                self._porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=["picovoice"],  # Default keyword
                )
                logger.info("Porcupine wake word engine initialized")
            except (ImportError, Exception) as exc:
                logger.warning("Porcupine not available: %s", exc)
        else:
            logger.info("PICOVOICE_ACCESS_KEY not set, wake word detection disabled")

        logger.info("Voice driver initialized (hardware mode)")

    def set_on_wake_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_wake_word = callback

    def set_on_stop_word(self, callback: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_stop_word = callback

    # ─── ASR ──────────────────────────────────────────────────

    async def recognize(
        self, language: str = "zh-CN", timeout_s: int = 10
    ) -> dict[str, Any]:
        """Recognize speech from microphone."""
        if self._mock:
            logger.info("Mock ASR: returning simulated text")
            await asyncio.sleep(0.1)
            return {"ok": True, "text": "[mock speech input]", "confidence": 0.95}

        import speech_recognition as sr

        try:
            with self._microphone as source:
                logger.info("Listening for speech (timeout=%ds)...", timeout_s)
                audio = await asyncio.to_thread(
                    self._recognizer.listen,
                    source,
                    timeout=timeout_s,
                    phrase_time_limit=timeout_s,
                )

            logger.info("Recognizing speech...")
            text = await asyncio.to_thread(
                self._recognizer.recognize_google,
                audio,
                language=language,
            )

            text_lower = text.strip().lower() if isinstance(text, str) else ""

            # Check for stop words — hardcoded, never goes through LLM
            if any(w in text_lower for w in STOP_WORDS):
                logger.warning("Stop word detected in speech: %s", text)
                if self._on_stop_word:
                    await self._on_stop_word()
                return {"ok": True, "text": text, "is_stop_word": True}

            return {"ok": True, "text": text, "confidence": 0.9}

        except sr.WaitTimeoutError:
            return {"ok": False, "error": "timeout", "text": ""}
        except sr.UnknownValueError:
            return {"ok": False, "error": "unrecognized", "text": ""}
        except sr.RequestError as exc:
            logger.error("ASR request error: %s", exc)
            return {"ok": False, "error": str(exc), "text": ""}

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
        self._pygame.mixer.music.load(path)
        self._pygame.mixer.music.play()
        while self._pygame.mixer.music.get_busy():
            time.sleep(0.05)

    # ─── Wake Word Detection ──────────────────────────────────

    async def listen_start(self) -> dict[str, Any]:
        """Start wake word detection loop."""
        if self._listening:
            return {"ok": True, "listening": True}

        self._listening = True
        self._cancel_event.clear()

        if self._mock:
            logger.info("Mock wake word detection started")
            return {"ok": True, "listening": True}

        if not self._porcupine:
            logger.warning("Porcupine not initialized, wake word detection unavailable")
            return {"ok": False, "error": "porcupine_not_available", "listening": False}

        self._listen_task = asyncio.create_task(self._wake_word_loop())
        return {"ok": True, "listening": True}

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
                audio_stream = pa.open(
                    rate=self._porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self._porcupine.frame_length,
                )

                logger.info("Wake word detection active")
                while self._listening:
                    pcm = audio_stream.read(
                        self._porcupine.frame_length, exception_on_overflow=False
                    )
                    pcm_unpacked = struct.unpack_from(
                        "h" * self._porcupine.frame_length, pcm
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
