"""Tests for the Aliyun ASR hotword setup helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_script() -> Any:
    script = Path(__file__).resolve().parents[2] / "scripts" / "create_aliyun_asr_hotwords.py"
    spec = importlib.util.spec_from_file_location("create_aliyun_asr_hotwords", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_phrase_id_from_finetune_response_object() -> None:
    module = _load_script()

    class Output:
        finetuned_output = "phrase-123"

    class Response:
        output = Output()

    assert module.extract_phrase_id(Response()) == "phrase-123"


def test_upsert_env_line_replaces_existing_phrase_id() -> None:
    module = _load_script()

    content = "DASHSCOPE_API_KEY=sk-test\nALIYUN_FUNASR_PHRASE_ID=old\n"

    assert module.upsert_env_line(content, "ALIYUN_FUNASR_PHRASE_ID", "phrase-123") == (
        "DASHSCOPE_API_KEY=sk-test\nALIYUN_FUNASR_PHRASE_ID=phrase-123\n"
    )


def test_parse_hotwords_clamps_to_dashscope_phrase_weight_range() -> None:
    module = _load_script()

    assert module.parse_hotwords(["前进:100", "噪音:-100"]) == {"前进": 5, "噪音": -6}


def test_select_hotword_model_does_not_use_runtime_asr_model_by_default() -> None:
    module = _load_script()

    assert (
        module.select_hotword_model(
            "",
            {
                "ALIYUN_FUNASR_MODEL": "fun-asr-realtime",
                "ALIYUN_FUNASR_HOTWORD_MODEL": "",
            },
        )
        == "paraformer-realtime-v1"
    )


def test_default_hotwords_include_motion_routines() -> None:
    module = _load_script()

    assert module.DEFAULT_HOTWORDS["转个圈"] == 5
    assert module.DEFAULT_HOTWORDS["跳个舞"] == 5
