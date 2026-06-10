#!/usr/bin/env python3
"""Run voice E2E probes against a running mcar Robot Service."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


VOICE_EVENT_TYPES = {
    "voice.turn.ok",
    "voice.turn.command",
    "voice.turn.no_input",
    "voice.turn.ignored",
    "voice.turn.stopped",
}


class RobotApiClient:
    def __init__(self, base_url: str, *, timeout_s: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def get_json(self, path: str) -> Any:
        return self._request_json("GET", path)

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request_json("POST", path, payload)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode())


def run_round(client: Any, *, round_index: int, source: str) -> dict[str, Any]:
    client.get_json("/api/status")
    before_ids = {event.get("id") for event in client.get_json("/api/audit")}

    start = time.monotonic()
    result = client.post_json("/api/voice/run_once", {"source": source})
    request_ms = int((time.monotonic() - start) * 1000)

    events = client.get_json("/api/audit")
    event = find_new_voice_event(events, before_ids, source=source)
    summary = summarize_voice_event(event, request_ms=request_ms)
    summary["round"] = round_index
    summary["run_once_result"] = result
    return summary


def find_new_voice_event(
    events: list[dict[str, Any]],
    before_ids: set[Any],
    *,
    source: str,
) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("id") in before_ids:
            continue
        if event.get("event_type") not in VOICE_EVENT_TYPES:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("source") != source:
            continue
        return event
    raise RuntimeError(f"No new voice turn audit event found for source={source}")


def summarize_voice_event(event: dict[str, Any], *, request_ms: int) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
    asr = payload.get("asr") if isinstance(payload.get("asr"), dict) else {}
    asr_meta = asr.get("metadata") if isinstance(asr.get("metadata"), dict) else {}
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else {}
    tts = payload.get("tts") if isinstance(payload.get("tts"), dict) else {}
    event_type = str(event.get("event_type", ""))
    return {
        "event_id": event.get("id", ""),
        "event_type": event_type,
        "timestamp": event.get("timestamp", ""),
        "source": payload.get("source", ""),
        "ok": event_type in {"voice.turn.ok", "voice.turn.command", "voice.turn.stopped"},
        "text": payload.get("text", ""),
        "reason": payload.get("reason") or payload.get("error") or "",
        "request_ms": request_ms,
        "total_ms": timing.get("total_ms"),
        "prompt_ms": timing.get("prompt_ms"),
        "asr_ms": timing.get("asr_ms"),
        "llm_ms": timing.get("llm_ms"),
        "tts_ms": timing.get("tts_ms"),
        "action_ms": timing.get("action_ms"),
        "asr_provider": asr_meta.get("provider", ""),
        "asr_mode": asr_meta.get("mode", ""),
        "llm_model": llm.get("model", ""),
        "tts_provider": tts.get("provider", ""),
        "tts_model": tts.get("model", ""),
    }


def format_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "round",
        "event_type",
        "text",
        "reason",
        "request_ms",
        "total_ms",
        "asr_ms",
        "llm_ms",
        "tts_ms",
        "action_ms",
        "asr_provider",
        "asr_mode",
        "llm_model",
        "tts_model",
    ]
    lines = [" | ".join(headers), " | ".join("---" for _ in headers)]
    for row in rows:
        lines.append(" | ".join(_cell(row.get(header)) for header in headers))
    return "\n".join(lines)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("|", "/")
    return text[:80]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run voice E2E probes and summarize audit timing.")
    parser.add_argument("--base-url", default="http://192.168.2.201:8080")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--source", default="e2e_probe")
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a table.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    client = RobotApiClient(args.base_url, timeout_s=args.timeout_s)
    rows: list[dict[str, Any]] = []
    try:
        for index in range(1, args.rounds + 1):
            print(f"Round {index}: speak after the wake prompt...", file=sys.stderr)
            rows.append(run_round(client, round_index=index, source=args.source))
    except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
        print(f"voice_e2e_probe failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(format_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
