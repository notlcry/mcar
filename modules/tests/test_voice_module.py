"""Tests for the Voice module capabilities (mock mode)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        assert "tool.voice.listen_start" in manifest["capabilities"]
        assert "tool.voice.listen_stop" in manifest["capabilities"]

    def test_capabilities(self, voice_module: VoiceModule) -> None:
        caps = voice_module.capabilities()
        assert len(caps) == 4
        cap_ids = [c["capability_id"] for c in caps]
        assert "tool.voice.recognize" in cap_ids
        assert "tool.voice.synthesize" in cap_ids
        assert "tool.voice.listen_start" in cap_ids
        assert "tool.voice.listen_stop" in cap_ids


class TestVoiceDriverASR:
    @pytest.mark.asyncio
    async def test_recognize_mock(self, voice_driver: VoiceDriver) -> None:
        result = await voice_driver.recognize(language="zh-CN", timeout_s=5)
        assert result["ok"] is True
        assert result["text"] == "[mock speech input]"
        assert result["confidence"] == 0.95


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


class TestVoiceDriverWakeWord:
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
