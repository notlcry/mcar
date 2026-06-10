"""Wake word provider abstraction."""

from __future__ import annotations

import importlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_FRAME_LENGTH = 1280


@dataclass(frozen=True)
class WakeWordDetection:
    detected: bool
    label: str
    score: float
    scores: dict[str, float]


class WakeWordProvider(Protocol):
    name: str
    label: str
    available: bool
    error: str | None
    sample_rate: int
    frame_length: int

    def process(self, pcm: Sequence[int]) -> WakeWordDetection:
        """Process one mono int16 PCM frame."""

    def close(self) -> None:
        """Release provider resources."""


class DisabledWakeWordProvider:
    def __init__(
        self,
        error: str = "wake word disabled",
        *,
        name: str = "disabled",
        label: str = "disabled",
    ) -> None:
        self.name = name
        self.label = label
        self.available = False
        self.error = error
        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.frame_length = DEFAULT_FRAME_LENGTH

    def process(self, pcm: Sequence[int]) -> WakeWordDetection:
        return WakeWordDetection(False, self.label, 0.0, {})

    def close(self) -> None:
        return None


class OpenWakeWordProvider:
    name = "openwakeword"
    available = True
    error = None
    sample_rate = DEFAULT_SAMPLE_RATE

    def __init__(
        self,
        *,
        wakeword_models: list[str],
        threshold: float = 0.5,
        inference_framework: str = "tflite",
        frame_length: int = DEFAULT_FRAME_LENGTH,
        enable_speex_noise_suppression: bool = False,
        vad_threshold: float = 0.0,
        debounce_s: float = 1.0,
    ) -> None:
        if not wakeword_models:
            raise ValueError("at least one openWakeWord model is required")

        model_module = importlib.import_module("openwakeword.model")
        model_class = getattr(model_module, "Model")
        self._model = model_class(
            wakeword_models=wakeword_models,
            inference_framework=inference_framework,
            enable_speex_noise_suppression=enable_speex_noise_suppression,
            vad_threshold=vad_threshold,
        )
        self.wakeword_models = wakeword_models
        self.threshold = max(0.0, min(1.0, threshold))
        self.inference_framework = inference_framework
        self.frame_length = frame_length
        self.debounce_s = max(0.0, debounce_s)
        self._last_detection_at = 0.0
        self.label = _model_label(wakeword_models[0])

    def process(self, pcm: Sequence[int]) -> WakeWordDetection:
        audio = _to_int16_audio(pcm)
        raw_scores = self._model.predict(audio) or {}
        scores = {str(label): float(score) for label, score in raw_scores.items()}
        if not scores:
            return WakeWordDetection(False, self.label, 0.0, {})

        label, score = max(scores.items(), key=lambda item: item[1])
        now = time.monotonic()
        detected = score >= self.threshold and now - self._last_detection_at >= self.debounce_s
        if detected:
            self._last_detection_at = now
        return WakeWordDetection(detected, label, score, scores)

    def close(self) -> None:
        return None


class PorcupineWakeWordProvider:
    name = "porcupine"
    available = True
    error = None

    def __init__(self, porcupine: Any, *, label: str, source: str) -> None:
        self._porcupine = porcupine
        self.label = label
        self.source = source
        self.sample_rate = int(porcupine.sample_rate)
        self.frame_length = int(porcupine.frame_length)

    def process(self, pcm: Sequence[int]) -> WakeWordDetection:
        keyword_index = int(self._porcupine.process(pcm))
        if keyword_index < 0:
            return WakeWordDetection(False, self.label, 0.0, {})
        return WakeWordDetection(True, self.label, 1.0, {self.label: 1.0})

    def close(self) -> None:
        self._porcupine.delete()


class _FallbackAudioArray:
    """Small numpy-like object for tests when numpy is not installed."""

    dtype = "int16"

    def __init__(self, samples: Sequence[int]) -> None:
        self._samples = [max(-32768, min(32767, int(sample))) for sample in samples]
        self.shape = (len(self._samples),)

    def __iter__(self) -> Any:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int) -> int:
        return self._samples[index]


def build_wake_word_provider(
    env: Mapping[str, str] | None = None,
    *,
    repo_root: Path | None = None,
) -> WakeWordProvider:
    values = env or {}
    provider_name = values.get("VOICE_WAKE_PROVIDER", "auto").strip().lower()
    root = repo_root or Path.cwd()

    if provider_name in {"none", "off", "disabled"}:
        return DisabledWakeWordProvider()
    if provider_name in {"openwakeword", "open_wake_word"}:
        return _build_openwakeword_provider(values)
    if provider_name in {"porcupine", "picovoice"}:
        return _build_porcupine_provider(values, root)
    if provider_name != "auto":
        return DisabledWakeWordProvider(
            f"unknown wake word provider: {provider_name}",
            name=provider_name or "unknown",
        )

    if _has_openwakeword_config(values):
        provider = _build_openwakeword_provider(values)
        if provider.available or not values.get("PICOVOICE_ACCESS_KEY", "").strip():
            return provider
        logger.warning("openWakeWord unavailable, falling back to Porcupine: %s", provider.error)

    if values.get("PICOVOICE_ACCESS_KEY", "").strip():
        return _build_porcupine_provider(values, root)

    return DisabledWakeWordProvider("no wake word provider configured")


def _build_openwakeword_provider(values: Mapping[str, str]) -> WakeWordProvider:
    models = _resolve_openwakeword_models(values)
    threshold = _parse_float(values.get("OPENWAKEWORD_THRESHOLD"), 0.5, 0.0, 1.0)
    frame_length = _parse_int(
        values.get("OPENWAKEWORD_FRAME_LENGTH"),
        DEFAULT_FRAME_LENGTH,
        160,
        4096,
    )
    debounce_s = _parse_float(values.get("OPENWAKEWORD_DEBOUNCE_S"), 1.0, 0.0, 30.0)
    vad_threshold = _parse_float(values.get("OPENWAKEWORD_VAD_THRESHOLD"), 0.0, 0.0, 1.0)
    inference_framework = (
        values.get("OPENWAKEWORD_INFERENCE_FRAMEWORK", "tflite").strip() or "tflite"
    )
    speex = _parse_bool(values.get("OPENWAKEWORD_ENABLE_SPEEX_NOISE_SUPPRESSION"), False)

    try:
        return OpenWakeWordProvider(
            wakeword_models=models,
            threshold=threshold,
            inference_framework=inference_framework,
            frame_length=frame_length,
            enable_speex_noise_suppression=speex,
            vad_threshold=vad_threshold,
            debounce_s=debounce_s,
        )
    except Exception as exc:
        return DisabledWakeWordProvider(
            f"openWakeWord not available: {exc}",
            name="openwakeword",
            label=_model_label(models[0]) if models else "openwakeword",
        )


def _build_porcupine_provider(values: Mapping[str, str], repo_root: Path) -> WakeWordProvider:
    access_key = values.get("PICOVOICE_ACCESS_KEY", "").strip()
    if not access_key:
        return DisabledWakeWordProvider(
            "PICOVOICE_ACCESS_KEY not set",
            name="porcupine",
            label="porcupine",
        )

    try:
        pvporcupine = importlib.import_module("pvporcupine")
    except Exception as exc:
        return DisabledWakeWordProvider(
            f"Porcupine not available: {exc}",
            name="porcupine",
            label="porcupine",
        )

    sensitivity = _parse_float(values.get("PICOVOICE_SENSITIVITY"), 0.55, 0.0, 1.0)
    builtin_keyword = values.get("PICOVOICE_BUILTIN_KEYWORD", "picovoice").strip() or "picovoice"
    keyword_path = _resolve_porcupine_keyword_path(values, repo_root)
    model_path = _resolve_porcupine_model_path(values, repo_root, keyword_path)

    base_kwargs: dict[str, Any] = {"access_key": access_key}
    if model_path:
        base_kwargs["model_path"] = str(model_path)

    last_error: str | None = None
    if keyword_path:
        kwargs = dict(base_kwargs)
        kwargs["keyword_paths"] = [str(keyword_path)]
        kwargs["sensitivities"] = [sensitivity]
        provider = _try_create_porcupine(
            pvporcupine,
            kwargs,
            label=keyword_path.name,
            source="keyword_path",
        )
        if provider.available:
            return provider
        last_error = provider.error

    kwargs = dict(base_kwargs)
    kwargs["keywords"] = [builtin_keyword]
    kwargs["sensitivities"] = [sensitivity]
    provider = _try_create_porcupine(
        pvporcupine,
        kwargs,
        label=builtin_keyword,
        source="builtin_keyword",
    )
    if provider.available:
        return provider

    return DisabledWakeWordProvider(
        provider.error or last_error or "Porcupine not available",
        name="porcupine",
        label=builtin_keyword,
    )


def _try_create_porcupine(
    pvporcupine: Any,
    kwargs: dict[str, Any],
    *,
    label: str,
    source: str,
) -> WakeWordProvider:
    try:
        porcupine = pvporcupine.create(**kwargs)
        logger.info(
            "Porcupine wake word engine initialized (wake_word=%s, source=%s)",
            label,
            source,
        )
        return PorcupineWakeWordProvider(porcupine, label=label, source=source)
    except Exception as exc:
        logger.warning("Porcupine init failed (source=%s): %s", source, exc)
        return DisabledWakeWordProvider(str(exc), name="porcupine", label=label)


def _resolve_openwakeword_models(values: Mapping[str, str]) -> list[str]:
    model_paths = _split_csv(values.get("OPENWAKEWORD_MODEL_PATH", ""))
    if model_paths:
        return [str(Path(path).expanduser()) for path in model_paths]

    model_names = _split_csv(values.get("OPENWAKEWORD_MODEL_NAME", ""))
    if model_names:
        return model_names

    return ["hey_jarvis"]


def _resolve_porcupine_keyword_path(values: Mapping[str, str], repo_root: Path) -> Path | None:
    raw_keyword_path = values.get("PICOVOICE_KEYWORD_PATH", "").strip()
    if raw_keyword_path:
        candidate = Path(raw_keyword_path).expanduser().resolve()
        if candidate.exists():
            return candidate
        logger.warning("PICOVOICE_KEYWORD_PATH does not exist: %s", candidate)
        return None

    for candidate in [
        repo_root / "legacy" / "src" / "wake_words" / "kk_zh_raspberry-pi_v3_0_0.ppn",
        repo_root / "legacy" / "wake_words" / "kk_zh_raspberry-pi_v3_0_0.ppn",
    ]:
        if candidate.exists():
            return candidate
    return None


def _resolve_porcupine_model_path(
    values: Mapping[str, str],
    repo_root: Path,
    keyword_path: Path | None,
) -> Path | None:
    raw_model_path = values.get("PICOVOICE_MODEL_PATH", "").strip()
    if raw_model_path:
        candidate = Path(raw_model_path).expanduser().resolve()
        if candidate.exists():
            return candidate
        logger.warning("PICOVOICE_MODEL_PATH does not exist: %s", candidate)
        return None

    if keyword_path:
        candidates = [
            keyword_path.parent / "porcupine_params_zh.pv",
            keyword_path.parent / "porcupine_params.pv",
        ]
        candidates.extend(sorted(keyword_path.parent.glob("porcupine_params*.pv")))
    else:
        candidates = [
            repo_root / "legacy" / "src" / "wake_words" / "porcupine_params_zh.pv",
            repo_root / "legacy" / "wake_words" / "porcupine_params_zh.pv",
            repo_root / "legacy" / "models" / "porcupine" / "porcupine_params_zh.pv",
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _to_int16_audio(samples: Sequence[int]) -> Any:
    try:
        import numpy as np

        return np.asarray(samples, dtype=np.int16)
    except ImportError:
        return _FallbackAudioArray(samples)


def _model_label(model: str) -> str:
    path = Path(model)
    if path.suffix:
        return path.stem
    return model


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(raw: str | None, default: float, lower: float, upper: float) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(lower, min(upper, value))


def _parse_int(raw: str | None, default: int, lower: int, upper: int) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(lower, min(upper, value))


def _has_openwakeword_config(values: Mapping[str, str]) -> bool:
    return any(
        values.get(key, "").strip()
        for key in (
            "OPENWAKEWORD_MODEL_PATH",
            "OPENWAKEWORD_MODEL_NAME",
            "OPENWAKEWORD_THRESHOLD",
            "OPENWAKEWORD_INFERENCE_FRAMEWORK",
        )
    )
