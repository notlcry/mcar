"""Voice module — speech recognition, TTS, wake word detection.

Capabilities:
  - tool.voice.recognize    — cloud ASR (Google STT)
  - tool.voice.synthesize   — Edge TTS (async, free, Chinese support)
  - tool.voice.listen_start — start wake word detection (Picovoice Porcupine)
  - tool.voice.listen_stop  — stop wake word detection
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.module_base import ModuleBase
from common.capability_spec import load_capabilities

try:
    from voice.driver import VoiceDriver
except ImportError:
    from driver import VoiceDriver


class VoiceModule(ModuleBase):
    """Voice I/O module: ASR + TTS + wake word detection."""

    def __init__(
        self,
        router_endpoint: str = "ipc:///tmp/mcar-router.sock",
        pub_endpoint: str = "ipc:///tmp/mcar-pub.sock",
        mock: bool = False,
    ) -> None:
        self._driver = VoiceDriver(mock=mock)
        self._driver.set_on_wake_word(self._emit_wake_word)
        self._driver.set_on_stop_word(self._emit_stop_word)
        super().__init__(router_endpoint=router_endpoint, pub_endpoint=pub_endpoint)

    def manifest(self) -> dict[str, Any]:
        return {
            "module_id": "voice",
            "module_version": "1.0.0",
            "description": "Voice I/O: ASR (Google STT), TTS (Edge TTS), wake word (Porcupine)",
            "capabilities": [
                "tool.voice.recognize",
                "tool.voice.synthesize",
                "tool.voice.listen_start",
                "tool.voice.listen_stop",
            ],
            "permissions_required": ["microphone", "speaker"],
        }

    def capabilities(self) -> list[dict[str, Any]]:
        caps_file = Path(__file__).parent / "capabilities.json"
        return load_capabilities(caps_file)

    async def invoke(
        self, capability_id: str, params: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if capability_id == "tool.voice.recognize":
            language = params.get("language", "zh-CN")
            timeout_s = params.get("timeout_s", 10)
            return await self._driver.recognize(language=language, timeout_s=timeout_s)

        if capability_id == "tool.voice.synthesize":
            text = params.get("text", "")
            voice = params.get("voice", "zh-CN-XiaoxiaoNeural")
            rate = params.get("rate", "+0%")
            return await self._driver.synthesize(text=text, voice=voice, rate=rate)

        if capability_id == "tool.voice.listen_start":
            return await self._driver.listen_start()

        if capability_id == "tool.voice.listen_stop":
            return await self._driver.listen_stop()

        raise ValueError(f"Unknown capability: {capability_id}")

    async def stop(self) -> None:
        """Emergency stop: stop all voice operations."""
        await self._driver.stop()

    async def cancel(self, invocation_id: str) -> None:
        """Cancel: stop ongoing voice operations."""
        await self._driver.stop()

    async def _emit_wake_word(self) -> None:
        """Emit wake word detected event via IPC."""
        await self._client.send_event("voice.wake_word_detected", {})

    async def _emit_stop_word(self) -> None:
        """Emit stop word detected event via IPC."""
        await self._client.send_event("voice.stop_word_detected", {})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice module for mcar")
    parser.add_argument("--router", default="ipc:///tmp/mcar-router.sock")
    parser.add_argument("--pub", default="ipc:///tmp/mcar-pub.sock")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    args = parser.parse_args()

    module = VoiceModule(
        router_endpoint=args.router,
        pub_endpoint=args.pub,
        mock=args.mock,
    )
    module.run_forever()
