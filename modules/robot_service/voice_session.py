"""Wake-word driven voice conversation session."""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING, Any

from .command_parser import is_ignorable_voice_text, parse_local_command

if TYPE_CHECKING:
    from .service import RobotService


class VoiceSession:
    def __init__(
        self,
        service: "RobotService",
        *,
        language: str = "zh-CN",
        timeout_s: int = 4,
        voice: str = "zh-CN-XiaoxiaoNeural",
    ) -> None:
        self._service = service
        self._language = language
        self._timeout_s = _env_int(
            os.environ.get("VOICE_COMMAND_TIMEOUT_S"),
            default=30,
            lower=1,
            upper=60,
        )
        self._voice = voice
        self._ack_text = os.environ.get("VOICE_ACK_TEXT", "我在。").strip()
        self._ack_enabled = _env_bool(os.environ.get("VOICE_ACK_ENABLED", "false"))
        self._wake_prompt_enabled = _env_bool(
            os.environ.get("VOICE_WAKE_PROMPT_ENABLED", "true")
        )
        self._wake_prompt = os.environ.get("VOICE_WAKE_PROMPT", "wake").strip() or "wake"
        self._reply_max_chars = _env_int(
            os.environ.get("VOICE_REPLY_MAX_CHARS"),
            default=80,
            lower=4,
            upper=200,
        )
        self._follow_up_enabled = _env_bool(
            os.environ.get("VOICE_FOLLOW_UP_ENABLED", "false")
        )
        self._follow_up_timeout_s = _env_int(
            os.environ.get("VOICE_FOLLOW_UP_TIMEOUT_S"),
            default=30,
            lower=1,
            upper=60,
        )
        self._follow_up_max_turns = _env_int(
            os.environ.get("VOICE_FOLLOW_UP_MAX_TURNS"),
            default=50,
            lower=0,
            upper=50,
        )
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[dict[str, Any]] | None = None

    def config_payload(self) -> dict[str, Any]:
        return {
            "follow_up_enabled": self._follow_up_enabled,
            "follow_up_timeout_s": self._follow_up_timeout_s,
            "follow_up_max_turns": self._follow_up_max_turns,
            "wake_prompt_enabled": self._wake_prompt_enabled,
            "command_timeout_s": self._timeout_s,
        }

    def attach(self) -> None:
        self._service.modules.voice.driver.set_on_wake_word(self.on_wake_word)
        self._service.modules.voice.driver.set_on_stop_word(self.on_stop_word)

    async def on_wake_word(self) -> None:
        if self._task and not self._task.done():
            self._service.audit("voice.turn.skipped", {"reason": "busy"})
            return
        self._task = asyncio.create_task(self.run_once(source="wake_word"))

    async def on_stop_word(self) -> None:
        await self._service.trigger_stop("voice")

    async def wait_idle(self) -> None:
        if self._task:
            await self._task

    async def run_once(self, *, source: str = "voice") -> dict[str, Any]:
        if self._lock.locked():
            self._service.audit("voice.turn.skipped", {"reason": "busy", "source": source})
            return {"ok": False, "reason": "busy"}

        async with self._lock:
            self._service.audit("voice.turn.started", {"source": source})
            await self._service.invoke("tool.voice.listen_stop", {})
            try:
                result = await self._run_conversation(
                    source,
                    prompt_enabled=self._wake_prompt_enabled,
                    timeout_s=self._timeout_s,
                )
                follow_up = await self._run_follow_up_turns(source, result)
                if follow_up:
                    result["follow_up"] = follow_up
                return result
            finally:
                if not self._service.state.estop_locked:
                    await self._service.invoke("tool.voice.listen_start", {})
                    await self._service.set_session_state("IDLE")

    async def _run_follow_up_turns(
        self,
        source: str,
        first_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not self._should_follow_up(first_result):
            return []

        results: list[dict[str, Any]] = []
        for turn in range(1, self._follow_up_max_turns + 1):
            result = await self._run_conversation(
                f"{source}:follow_up_{turn}",
                prompt_enabled=False,
                timeout_s=self._follow_up_timeout_s,
            )
            if not result.get("ok"):
                break
            results.append(result)
            if not self._should_follow_up(result):
                break
        return results

    def _should_follow_up(self, result: dict[str, Any]) -> bool:
        if not self._follow_up_enabled or self._follow_up_max_turns <= 0:
            return False
        if self._service.state.estop_locked or result.get("stopped"):
            return False
        return bool(result.get("ok"))

    async def _run_conversation(
        self,
        source: str,
        *,
        prompt_enabled: bool,
        timeout_s: int,
    ) -> dict[str, Any]:
        turn_start = time.monotonic()
        timing: dict[str, int] = {}
        if prompt_enabled:
            self._service.state.set("session", "PROMPTING")
            prompt_start = time.monotonic()
            await self._play_wake_prompt()
            timing["prompt_ms"] = _elapsed_ms(prompt_start)
        await self._service.set_session_state("LISTENING")
        ack_task = self._start_ack()
        asr_start = time.monotonic()
        recognized = await self._service.invoke(
            "tool.voice.recognize",
            {"language": self._language, "timeout_s": timeout_s},
        )
        timing["asr_ms"] = _elapsed_ms(asr_start)
        asr = _asr_audit_payload(recognized.data)
        if not recognized.success or not recognized.data or not recognized.data.get("ok"):
            error = recognized.error.message if recognized.error else recognized.data
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload: dict[str, Any] = {"source": source, "error": error, "timing": timing}
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.no_input",
                payload,
            )
            await self._wait_ack(ack_task)
            return {"ok": False, "reason": "no_input"}

        text = str(recognized.data.get("text") or "").strip()
        if not text:
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {"source": source, "error": "empty", "timing": timing}
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.no_input",
                payload,
            )
            await self._wait_ack(ack_task)
            return {"ok": False, "reason": "no_input"}

        if recognized.data.get("is_stop_word"):
            await self._service.trigger_stop("voice")
            await self._cancel_ack(ack_task)
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {"source": source, "text": text, "timing": timing}
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.stopped",
                payload,
            )
            return {"ok": True, "stopped": True}

        if is_ignorable_voice_text(text):
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {
                "source": source,
                "text": text,
                "reason": "ignored_asr_noise",
                "timing": timing,
            }
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.ignored",
                payload,
            )
            await self._wait_ack(ack_task)
            return {"ok": False, "reason": "ignored_asr_noise", "text": text}

        local_command = parse_local_command(text)
        if local_command is not None:
            result = await self._run_local_command(
                local_command,
                text=text,
                source=source,
                timing=timing,
                turn_start=turn_start,
                asr=asr,
            )
            if result.get("stopped"):
                await self._cancel_ack(ack_task)
            else:
                await self._wait_ack(ack_task)
            return result

        await self._service.set_session_state("THINKING")
        llm_start = time.monotonic()
        response = await self._service.chat(self._voice_prompt(text))
        timing["llm_ms"] = _elapsed_ms(llm_start)
        llm = _llm_audit_payload(self._service)
        response = self._shorten_response(response)
        if self._service.state.estop_locked:
            await self._cancel_ack(ack_task)
            return {"ok": True, "stopped": True}

        await self._wait_ack(ack_task)
        await self._service.set_session_state("RESPONDING")
        tts_start = time.monotonic()
        tts_result = await self._service.invoke(
            "tool.voice.synthesize",
            {"text": response, "voice": self._voice},
        )
        timing["tts_ms"] = _elapsed_ms(tts_start)
        tts = _tts_audit_payload(tts_result.data)
        timing["total_ms"] = _elapsed_ms(turn_start)
        payload = {
            "source": source,
            "text": text,
            "response_length": len(response),
            "timing": timing,
        }
        if asr is not None:
            payload["asr"] = asr
        if llm is not None:
            payload["llm"] = llm
        if tts is not None:
            payload["tts"] = tts
        self._service.audit(
            "voice.turn.ok",
            payload,
        )
        return {"ok": True, "text": text, "response": response}

    async def _run_local_command(
        self,
        command: Any,
        *,
        text: str,
        source: str,
        timing: dict[str, int],
        turn_start: float,
        asr: dict[str, Any] | None,
    ) -> dict[str, Any]:
        action_start = time.monotonic()
        if command.kind == "stop":
            await self._service.trigger_stop("voice_command")
            timing["action_ms"] = _elapsed_ms(action_start)
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {"source": source, "text": text, "command": "stop", "timing": timing}
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.command",
                payload,
            )
            return {"ok": True, "handled_locally": True, "command": "stop", "stopped": True}

        if command.kind == "move" and command.move is not None:
            await self._service.set_session_state("ACTING")
            result = await self._service.move(command.move)
            timing["action_ms"] = _elapsed_ms(action_start)
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {
                "source": source,
                "text": text,
                "command": "move",
                "direction": command.move.direction,
                "success": result.success,
                "timing": timing,
            }
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.command",
                payload,
            )
            if not result.success:
                error = result.error.message if result.error else "command failed"
                return {
                    "ok": False,
                    "handled_locally": True,
                    "command": "move",
                    "reason": error,
                }
            return {
                "ok": True,
                "handled_locally": True,
                "command": "move",
                "text": text,
                "result": result.data,
            }

        if command.kind == "routine" and command.routine is not None:
            await self._service.set_session_state("ACTING")
            result = await self._service.run_routine(command.routine)
            timing["action_ms"] = _elapsed_ms(action_start)
            timing["total_ms"] = _elapsed_ms(turn_start)
            payload = {
                "source": source,
                "text": text,
                "command": "routine",
                "routine": command.routine.name,
                "step_count": len(command.routine.steps),
                "success": result.success,
                "timing": timing,
            }
            if asr is not None:
                payload["asr"] = asr
            self._service.audit(
                "voice.turn.command",
                payload,
            )
            if not result.success:
                error = result.error.message if result.error else "routine failed"
                return {
                    "ok": False,
                    "handled_locally": True,
                    "command": "routine",
                    "routine": command.routine.name,
                    "reason": error,
                }
            return {
                "ok": True,
                "handled_locally": True,
                "command": "routine",
                "routine": command.routine.name,
                "text": text,
                "result": result.data,
            }

        return {"ok": False, "handled_locally": True, "command": command.kind}

    def _start_ack(self) -> asyncio.Task[Any] | None:
        if not self._ack_enabled or not self._ack_text:
            return None
        return asyncio.create_task(
            self._service.invoke(
                "tool.voice.synthesize",
                {"text": self._ack_text, "voice": self._voice},
            )
        )

    async def _play_wake_prompt(self) -> None:
        result = await self._service.invoke(
            "tool.voice.play_prompt",
            {"prompt": self._wake_prompt},
        )
        if not result.success:
            error = result.error.message if result.error else "unknown"
            self._service.audit("voice.prompt.failed", {"prompt": self._wake_prompt, "error": error})
            return
        data = result.data or {}
        if not data.get("ok", False):
            self._service.audit(
                "voice.prompt.failed",
                {"prompt": self._wake_prompt, "error": data.get("error", "unknown")},
            )

    async def _wait_ack(self, task: asyncio.Task[Any] | None) -> None:
        if task is None:
            return
        result = await task
        if not result.success:
            error = result.error.message if result.error else "unknown"
            self._service.audit("voice.ack.failed", {"error": error})

    async def _cancel_ack(self, task: asyncio.Task[Any] | None) -> None:
        if task is None:
            return
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._service.audit("voice.ack.failed", {"error": str(exc)})

    def _voice_prompt(self, text: str) -> str:
        return (
            f"{text}\n\n"
            "语音回复要求：请用一句话直接回答，不解释过程，"
            f"最多 {self._reply_max_chars} 个中文字。"
        )

    def _shorten_response(self, response: str) -> str:
        cleaned = " ".join(response.strip().split())
        if len(cleaned) <= self._reply_max_chars:
            return cleaned
        return cleaned[: self._reply_max_chars]


def _asr_audit_payload(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    payload: dict[str, Any] = {}
    confidence = data.get("confidence")
    if isinstance(confidence, int | float):
        payload["confidence"] = float(confidence)
    metadata = data.get("metadata")
    if isinstance(metadata, dict) and metadata:
        payload["metadata"] = dict(metadata)
    return payload or None


def _llm_audit_payload(service: Any) -> dict[str, Any] | None:
    agent = getattr(service, "agent", None)
    model = getattr(agent, "model", None)
    if not isinstance(model, str) or not model:
        return None
    return {"model": model}


def _tts_audit_payload(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    payload: dict[str, Any] = {}
    for key in ("provider", "model", "voice"):
        value = data.get(key)
        if isinstance(value, str) and value:
            payload[key] = value
    return payload or None


def _env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(raw: str | None, *, default: int, lower: int, upper: int) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(lower, min(upper, value))


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
