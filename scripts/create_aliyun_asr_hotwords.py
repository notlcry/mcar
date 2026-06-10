#!/usr/bin/env python3
"""Create or update an Aliyun DashScope ASR hotword phrase resource."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http import HTTPStatus
from pathlib import Path
from typing import Any


DEFAULT_HOTWORD_MODEL = "paraformer-realtime-v1"
DEFAULT_HOTWORDS = {
    "前进": 5,
    "向前": 5,
    "向前走": 5,
    "往前": 5,
    "往前走": 5,
    "后退": 5,
    "向后": 5,
    "向后退": 5,
    "左转": 5,
    "向左转": 5,
    "右转": 5,
    "向右转": 5,
    "转圈": 5,
    "转个圈": 5,
    "转一圈": 5,
    "原地转圈": 5,
    "原地转一圈": 5,
    "跳舞": 5,
    "跳个舞": 5,
    "表演一下": 5,
    "停止": 5,
    "停车": 5,
    "急停": 5,
    "小车": 4,
    "机器人": 4,
}


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file)
    env_values = load_env_file(env_file) if env_file.exists() else {}
    api_key = env_values.get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", "")
    api_key = api_key.strip()
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required in env or --env-file")

    model = select_hotword_model(args.model, env_values)
    workspace = args.workspace or env_values.get("DASHSCOPE_WORKSPACE")
    phrases = dict(DEFAULT_HOTWORDS)
    phrases.update(parse_hotwords(args.hotword))

    phrase_id = env_values.get("ALIYUN_FUNASR_PHRASE_ID", "").strip()
    response_phrase_id, action = create_or_update_phrases(
        api_key=api_key,
        model=model,
        phrases=phrases,
        workspace=workspace,
        existing_phrase_id=phrase_id,
        force_create=args.force_create,
    )
    phrase_id = response_phrase_id or phrase_id
    if not phrase_id:
        raise SystemExit("DashScope did not return a phrase id")

    env_file_updated = False
    if args.write_env:
        original = env_file.read_text() if env_file.exists() else ""
        updated = upsert_env_line(original, "ALIYUN_FUNASR_PHRASE_ID", phrase_id)
        env_file.write_text(updated)
        env_file_updated = True

    print(
        json.dumps(
            {
                "ok": True,
                "action": action,
                "model": model,
                "phrase_id": phrase_id,
                "hotword_count": len(phrases),
                "env_file": str(env_file),
                "env_file_updated": env_file_updated,
            },
            ensure_ascii=False,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".ai_pet_env")
    parser.add_argument("--model", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--hotword", action="append", default=[], help="Extra hotword as WORD:WEIGHT")
    parser.add_argument("--force-create", action="store_true")
    parser.add_argument("--write-env", action="store_true")
    return parser.parse_args()


def select_hotword_model(args_model: str, env_values: dict[str, str]) -> str:
    return (
        args_model.strip()
        or env_values.get("ALIYUN_FUNASR_HOTWORD_MODEL", "").strip()
        or os.environ.get("ALIYUN_FUNASR_HOTWORD_MODEL", "").strip()
        or DEFAULT_HOTWORD_MODEL
    )


def create_or_update_phrases(
    *,
    api_key: str,
    model: str,
    phrases: dict[str, int],
    workspace: str | None,
    existing_phrase_id: str,
    force_create: bool,
) -> tuple[str, str]:
    try:
        import dashscope
        from dashscope.audio.asr import AsrPhraseManager
    except ImportError as exc:
        raise SystemExit("dashscope is required: pip install dashscope") from exc

    dashscope.api_key = api_key
    if existing_phrase_id and not force_create:
        response = AsrPhraseManager.update_phrases(
            model=model,
            phrase_id=existing_phrase_id,
            phrases=phrases,
            workspace=workspace or None,
            api_key=api_key,
        )
        ensure_success(response)
        return extract_phrase_id(response) or existing_phrase_id, "updated"

    response = AsrPhraseManager.create_phrases(
        model=model,
        phrases=phrases,
        workspace=workspace or None,
        api_key=api_key,
    )
    ensure_success(response)
    return extract_phrase_id(response), "created"


def ensure_success(response: Any) -> None:
    status_code = getattr(response, "status_code", None)
    if status_code == HTTPStatus.OK or status_code == 200:
        return
    code = getattr(response, "code", "")
    message = getattr(response, "message", "")
    request_id = getattr(response, "request_id", "")
    raise SystemExit(
        f"DashScope hotword request failed: status={status_code} code={code} "
        f"message={message} request_id={request_id}"
    )


def extract_phrase_id(response: Any) -> str:
    output = getattr(response, "output", None)
    for field in ("finetuned_output", "job_id", "id"):
        value = getattr(output, field, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(output, dict):
        for field in ("finetuned_output", "job_id", "id"):
            value = output.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def parse_hotwords(items: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for item in items:
        word, sep, raw_weight = item.partition(":")
        word = word.strip()
        if not word or not sep:
            raise SystemExit(f"Invalid --hotword {item!r}, expected WORD:WEIGHT")
        try:
            weight = int(raw_weight)
        except ValueError as exc:
            raise SystemExit(f"Invalid hotword weight in {item!r}") from exc
        parsed[word] = clamp_phrase_weight(weight)
    return parsed


def clamp_phrase_weight(weight: int) -> int:
    if weight == 0:
        return 1
    return max(-6, min(5, weight))


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        key, sep, value = stripped.partition("=")
        if not sep:
            continue
        values[key.strip()] = unquote_env_value(value.strip())
    return values


def unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def upsert_env_line(content: str, key: str, value: str) -> str:
    line = f"{key}={value}"
    lines = content.splitlines()
    for index, existing in enumerate(lines):
        stripped = existing.strip()
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if stripped.startswith(f"{key}="):
            lines[index] = line
            return "\n".join(lines) + "\n"
    if content and not content.endswith("\n"):
        content += "\n"
    return content + line + "\n"


if __name__ == "__main__":
    sys.exit(main())
