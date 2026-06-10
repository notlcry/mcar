#!/usr/bin/env python3
"""Local Qwen3-ASR HTTP server for mcar."""

from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile


app = FastAPI(title="mcar Qwen3-ASR Local Service")
_engine: "Qwen3AsrEngine | None" = None


class Qwen3AsrEngine:
    def __init__(
        self,
        *,
        model_name: str,
        device_map: str | None,
        dtype_name: str | None,
        max_new_tokens: int,
        max_inference_batch_size: int,
    ) -> None:
        import torch
        from qwen_asr import Qwen3ASRModel

        kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "max_inference_batch_size": max_inference_batch_size,
        }
        if device_map:
            kwargs["device_map"] = device_map
        if dtype_name:
            kwargs["dtype"] = _torch_dtype(torch, dtype_name)

        self.model_name = model_name
        self.model = Qwen3ASRModel.from_pretrained(model_name, **kwargs)

    def transcribe(self, audio_path: Path, language: str | None) -> dict[str, str | None]:
        results = self.model.transcribe(
            audio=str(audio_path),
            language=language or None,
        )
        result = results[0]
        return {
            "text": str(getattr(result, "text", "")).strip(),
            "language": getattr(result, "language", language),
        }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "loaded": _engine is not None,
        "model": os.environ.get("QWEN3_ASR_MODEL", "Qwen/Qwen3-ASR-0.6B"),
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> dict[str, Any]:
    engine = _get_engine()
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp_path = Path(tmp.name)

    started = time.perf_counter()
    try:
        result = engine.transcribe(tmp_path, language)
        return {
            **result,
            "duration_s": round(time.perf_counter() - started, 3),
            "model": engine.model_name,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def _get_engine() -> Qwen3AsrEngine:
    global _engine
    if _engine is None:
        _engine = Qwen3AsrEngine(
            model_name=os.environ.get("QWEN3_ASR_MODEL", "Qwen/Qwen3-ASR-0.6B"),
            device_map=_optional_env("QWEN3_ASR_DEVICE_MAP", "auto"),
            dtype_name=_optional_env("QWEN3_ASR_DTYPE", "float32"),
            max_new_tokens=int(os.environ.get("QWEN3_ASR_MAX_NEW_TOKENS", "256")),
            max_inference_batch_size=int(
                os.environ.get("QWEN3_ASR_MAX_INFERENCE_BATCH_SIZE", "1")
            ),
        )
    return _engine


def _optional_env(key: str, default: str) -> str | None:
    value = os.environ.get(key, default).strip()
    return value if value and value.lower() != "none" else None


def _torch_dtype(torch: Any, name: str) -> Any:
    dtype = getattr(torch, name, None)
    if dtype is None:
        raise ValueError(f"Unsupported torch dtype: {name}")
    return dtype


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Qwen3-ASR server")
    parser.add_argument("--host", default=os.environ.get("QWEN3_ASR_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QWEN3_ASR_PORT", "8765")))
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
