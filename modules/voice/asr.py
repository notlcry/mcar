"""ASR provider implementations for the voice driver."""

from __future__ import annotations

import io
import json
import os
import time
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


DEFAULT_ALIYUN_NLS_URL = "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"
DEFAULT_DASHSCOPE_WEBSOCKET_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
DEFAULT_ALIYUN_FUNASR_MODEL = "fun-asr-realtime"


@dataclass(frozen=True)
class AsrResult:
    text: str
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AsrProvider(Protocol):
    name: str

    def recognize(self, audio: Any, language: str) -> AsrResult:
        ...


class GoogleAsrProvider:
    name = "google"

    def __init__(self, recognizer: Any) -> None:
        self.recognizer = recognizer

    def recognize(self, audio: Any, language: str) -> AsrResult:
        text = self.recognizer.recognize_google(audio, language=language)
        return AsrResult(text=str(text), confidence=0.9)


class WhisperAsrProvider:
    name = "whisper"

    def __init__(self, url: str) -> None:
        clean_url = url.strip().rstrip("/")
        self.url = f"{clean_url}/transcribe" if clean_url else ""

    def recognize(self, audio: Any, language: str) -> AsrResult:
        wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
        boundary = "----WhisperBoundary"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
        body.write(b"Content-Type: audio/wav\r\n\r\n")
        body.write(wav_data)
        body.write(f"\r\n--{boundary}--\r\n".encode())

        lang = language.split("-", 1)[0] if "-" in language else language
        req = urllib.request.Request(
            f"{self.url}?task=transcribe&language={lang}",
            data=body.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())

        text = str(payload.get("text", "")).strip()
        audio_seconds = float(payload.get("audio_seconds", 0) or 0)
        return AsrResult(text=text, confidence=None, metadata={"audio_seconds": audio_seconds})


class AliyunFunAsrRealtimeProvider:
    name = "aliyun_funasr_realtime"

    def __init__(
        self,
        *,
        api_key: str,
        websocket_url: str = DEFAULT_DASHSCOPE_WEBSOCKET_URL,
        model: str = DEFAULT_ALIYUN_FUNASR_MODEL,
        sample_rate: int = 16000,
        chunk_size: int = 3200,
        chunk_interval_s: float = 0.1,
        max_sentence_silence_ms: int = 800,
        semantic_punctuation_enabled: bool = False,
        language_hint: str | None = None,
        speech_noise_threshold: float | None = None,
        phrase_id: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.websocket_url = websocket_url
        self.model = model
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.chunk_interval_s = chunk_interval_s
        self.max_sentence_silence_ms = max_sentence_silence_ms
        self.semantic_punctuation_enabled = semantic_punctuation_enabled
        self.language_hint = language_hint
        self.speech_noise_threshold = speech_noise_threshold
        self.phrase_id = phrase_id

    def recognize(self, audio: Any, language: str) -> AsrResult:
        session = self.start_stream(language)
        pcm = audio.get_raw_data(convert_rate=self.sample_rate, convert_width=2)
        for offset in range(0, len(pcm), self.chunk_size):
            session.send_pcm(pcm[offset : offset + self.chunk_size])
            if self.chunk_interval_s > 0:
                time.sleep(self.chunk_interval_s)
        return session.finish()

    def start_stream(self, language: str) -> "AliyunFunAsrStreamSession":
        return AliyunFunAsrStreamSession(self, language)

    def _optional_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.speech_noise_threshold is not None:
            kwargs["speech_noise_threshold"] = self.speech_noise_threshold
        return kwargs


class AliyunFunAsrStreamSession:
    def __init__(self, provider: AliyunFunAsrRealtimeProvider, language: str) -> None:
        import dashscope
        from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

        dashscope.api_key = provider.api_key
        dashscope.base_websocket_api_url = provider.websocket_url
        self._recognition_result = RecognitionResult
        self._final_sentences: list[str] = []
        self._partial_texts: list[str] = []
        self._errors: list[str] = []
        self._metadata: dict[str, Any] = {}
        self._latest_text = ""
        self._closed = False

        session = self

        class Callback(RecognitionCallback):
            def on_open(self) -> None:
                pass

            def on_close(self) -> None:
                pass

            def on_complete(self) -> None:
                pass

            def on_error(self, result: Any) -> None:
                session._errors.append(_dashscope_error_message(result))

            def on_event(self, result: Any) -> None:
                sentence = result.get_sentence()
                if not isinstance(sentence, dict):
                    return
                text = str(sentence.get("text", "")).strip()
                if not text:
                    return
                session._latest_text = text
                request_id = _safe_call(result, "get_request_id")
                if request_id is not None:
                    session._metadata["request_id"] = request_id
                if session._recognition_result.is_sentence_end(sentence):
                    session._final_sentences.append(text)
                    usage = _safe_call(result, "get_usage", sentence)
                    if usage is not None:
                        session._metadata["usage"] = usage
                else:
                    session._partial_texts.append(text)

        self._recognition = Recognition(
            model=provider.model,
            format="pcm",
            sample_rate=provider.sample_rate,
            semantic_punctuation_enabled=provider.semantic_punctuation_enabled,
            max_sentence_silence=provider.max_sentence_silence_ms,
            punctuation_prediction_enabled=True,
            language_hints=[provider.language_hint or _dashscope_language_hint(language)],
            callback=Callback(),
            **provider._optional_kwargs(),
        )
        if provider.phrase_id:
            self._recognition.start(phrase_id=provider.phrase_id)
        else:
            self._recognition.start()

    def send_pcm(self, pcm: bytes) -> None:
        if self._closed:
            raise RuntimeError("ASR stream is already closed")
        self._recognition.send_audio_frame(pcm)

    def finish(self) -> AsrResult:
        if not self._closed:
            self._recognition.stop()
            self._closed = True
        if self._errors and not self._final_sentences and not self._latest_text:
            raise RuntimeError(self._errors[-1])
        if self._partial_texts:
            self._metadata["partial_texts"] = self._partial_texts
        _add_if_not_none(
            self._metadata,
            "request_id",
            _safe_call(self._recognition, "get_last_request_id"),
        )
        _add_if_not_none(
            self._metadata,
            "first_package_delay_ms",
            _safe_call(self._recognition, "get_first_package_delay"),
        )
        _add_if_not_none(
            self._metadata,
            "last_package_delay_ms",
            _safe_call(self._recognition, "get_last_package_delay"),
        )
        text = "".join(self._final_sentences).strip() or self._latest_text
        return AsrResult(text=text, confidence=None, metadata=self._metadata)


class AliyunNlsAsrProvider:
    name = "aliyun_nls"

    def __init__(
        self,
        *,
        appkey: str,
        token: str,
        url: str = DEFAULT_ALIYUN_NLS_URL,
        sample_rate: int = 16000,
        chunk_size: int = 640,
        chunk_interval_s: float = 0.01,
    ) -> None:
        self.appkey = appkey
        self.token = token
        self.url = url
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.chunk_interval_s = chunk_interval_s

    def recognize(self, audio: Any, language: str) -> AsrResult:
        import nls

        sentences: list[str] = []
        confidence: float | None = None
        errors: list[str] = []

        def on_sentence_end(message: str, *args: Any) -> None:
            nonlocal confidence
            payload = _json_payload(message)
            result = str(payload.get("result", "")).strip()
            if result:
                sentences.append(result)
            raw_confidence = payload.get("confidence")
            if isinstance(raw_confidence, int | float):
                confidence = float(raw_confidence)

        def on_error(message: str, *args: Any) -> None:
            errors.append(message)

        transcriber = nls.NlsSpeechTranscriber(
            url=self.url,
            token=self.token,
            appkey=self.appkey,
            on_sentence_end=on_sentence_end,
            on_error=on_error,
            on_close=lambda *args: None,
            on_start=lambda *args: None,
            on_result_changed=lambda *args: None,
            on_completed=lambda *args: None,
        )
        ok = transcriber.start(
            aformat="pcm",
            sample_rate=self.sample_rate,
            enable_intermediate_result=False,
            enable_punctuation_prediction=True,
            enable_inverse_text_normalization=True,
        )
        if not ok:
            raise RuntimeError("Aliyun NLS transcriber failed to start")

        pcm = audio.get_raw_data(convert_rate=self.sample_rate, convert_width=2)
        for offset in range(0, len(pcm), self.chunk_size):
            transcriber.send_audio(pcm[offset : offset + self.chunk_size])
            if self.chunk_interval_s > 0:
                time.sleep(self.chunk_interval_s)
        transcriber.stop(timeout=10)

        if errors and not sentences:
            raise RuntimeError(errors[-1])
        return AsrResult(text="".join(sentences).strip(), confidence=confidence)


class Qwen3AsrLocalProvider:
    name = "qwen3_asr_local"

    def __init__(
        self,
        *,
        url: str,
        timeout_s: int = 300,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> None:
        self.url = _transcribe_url(url)
        self.timeout_s = timeout_s
        self.sample_rate = sample_rate
        self.language = language

    def recognize(self, audio: Any, language: str) -> AsrResult:
        wav_data = audio.get_wav_data(convert_rate=self.sample_rate, convert_width=2)
        fields = {"language": self.language or _qwen3_language(language)}
        body, content_type = _multipart_audio(wav_data, fields)
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=self.timeout_s) as resp:
            payload = json.loads(resp.read().decode())

        text = str(payload.get("text", "")).strip()
        confidence = payload.get("confidence")
        metadata = _qwen3_metadata(payload)
        return AsrResult(
            text=text,
            confidence=float(confidence) if isinstance(confidence, int | float) else None,
            metadata=metadata,
        )


def build_asr_provider(env: Mapping[str, str] | None, google_recognizer: Any) -> AsrProvider:
    source = env if env is not None else os.environ
    provider = source.get("VOICE_ASR_PROVIDER", "auto").strip().lower()
    if provider == "auto":
        if source.get("DASHSCOPE_API_KEY"):
            provider = "aliyun_funasr_realtime"
        elif source.get("ALIYUN_NLS_APPKEY") or source.get("ALIYUN_NLS_TOKEN"):
            provider = "aliyun_nls"
        elif source.get("QWEN3_ASR_URL"):
            provider = "qwen3_asr_local"
        elif source.get("WHISPER_URL"):
            provider = "whisper"
        else:
            provider = "google"

    if provider in {"aliyun_funasr", "aliyun_funasr_realtime", "funasr", "funasr_realtime"}:
        return AliyunFunAsrRealtimeProvider(
            api_key=_required(source, "DASHSCOPE_API_KEY"),
            websocket_url=source.get("DASHSCOPE_WEBSOCKET_URL", DEFAULT_DASHSCOPE_WEBSOCKET_URL),
            model=source.get("ALIYUN_FUNASR_MODEL", DEFAULT_ALIYUN_FUNASR_MODEL),
            sample_rate=int(source.get("ALIYUN_FUNASR_SAMPLE_RATE", "16000")),
            chunk_size=int(source.get("ALIYUN_FUNASR_CHUNK_SIZE", "3200")),
            chunk_interval_s=float(source.get("ALIYUN_FUNASR_CHUNK_INTERVAL_S", "0.1")),
            max_sentence_silence_ms=int(source.get("ALIYUN_FUNASR_MAX_SENTENCE_SILENCE_MS", "800")),
            semantic_punctuation_enabled=_env_bool(
                source.get("ALIYUN_FUNASR_SEMANTIC_PUNCTUATION", "false")
            ),
            language_hint=_optional_text(source, "ALIYUN_FUNASR_LANGUAGE_HINT"),
            speech_noise_threshold=_optional_float(source, "ALIYUN_FUNASR_SPEECH_NOISE_THRESHOLD"),
            phrase_id=_optional_text(source, "ALIYUN_FUNASR_PHRASE_ID"),
        )
    if provider in {"aliyun", "aliyun_nls", "nls"}:
        return AliyunNlsAsrProvider(
            appkey=_required(source, "ALIYUN_NLS_APPKEY"),
            token=_required(source, "ALIYUN_NLS_TOKEN"),
            url=source.get("ALIYUN_NLS_URL", DEFAULT_ALIYUN_NLS_URL),
            sample_rate=int(source.get("ALIYUN_NLS_SAMPLE_RATE", "16000")),
        )
    if provider in {"qwen", "qwen3", "qwen3_asr", "qwen3_asr_local"}:
        return Qwen3AsrLocalProvider(
            url=_required(source, "QWEN3_ASR_URL"),
            timeout_s=int(source.get("QWEN3_ASR_TIMEOUT_S", "300")),
            sample_rate=int(source.get("QWEN3_ASR_SAMPLE_RATE", "16000")),
            language=_optional_text(source, "QWEN3_ASR_LANGUAGE"),
        )
    if provider == "whisper":
        return WhisperAsrProvider(_required(source, "WHISPER_URL"))
    if provider == "google":
        return GoogleAsrProvider(google_recognizer)
    raise ValueError(f"Unsupported VOICE_ASR_PROVIDER: {provider}")


def _required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key, "").strip()
    return value or None


def _optional_float(env: Mapping[str, str], key: str) -> float | None:
    value = env.get(key, "").strip()
    return float(value) if value else None


def _env_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _json_payload(message: str) -> dict[str, Any]:
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return {}
    payload = data.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _dashscope_language_hint(language: str) -> str:
    normalized = language.strip().lower()
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("ja"):
        return "ja"
    return "zh"


def _qwen3_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized.startswith("zh"):
        return "Chinese"
    if normalized.startswith("en"):
        return "English"
    if normalized.startswith("ja"):
        return "Japanese"
    if normalized.startswith("ko"):
        return "Korean"
    if normalized.startswith(("yue", "cantonese")):
        return "Cantonese"
    return "Chinese"


def _dashscope_error_message(result: Any) -> str:
    message = getattr(result, "message", None)
    if message:
        return str(message)
    return str(result)


def _safe_call(obj: Any, method: str, *args: Any) -> Any:
    func = getattr(obj, method, None)
    if not callable(func):
        return None
    return func(*args)


def _add_if_not_none(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _transcribe_url(url: str) -> str:
    clean_url = url.strip().rstrip("/")
    if clean_url.endswith("/transcribe"):
        return clean_url
    return f"{clean_url}/transcribe"


def _multipart_audio(wav_data: bytes, fields: Mapping[str, str]) -> tuple[bytes, str]:
    boundary = "----McarAsrBoundary"
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(str(value).encode())
        body.write(b"\r\n")
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
    body.write(b"Content-Type: audio/wav\r\n\r\n")
    body.write(wav_data)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def _qwen3_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in ("language", "duration_s", "request_id"):
        if key in payload:
            metadata[key] = payload[key]
    return metadata
