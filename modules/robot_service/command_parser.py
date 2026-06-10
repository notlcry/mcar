"""Local deterministic command parser for short robot voice commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .agent import MoveCommand


CommandKind = Literal["move", "stop", "routine"]
RoutineName = Literal["spin", "dance"]


@dataclass(frozen=True)
class RoutineCommand:
    name: RoutineName
    steps: tuple[MoveCommand, ...]


@dataclass(frozen=True)
class LocalCommand:
    kind: CommandKind
    move: MoveCommand | None = None
    routine: RoutineCommand | None = None


_FILLERS = {
    "",
    "嗯",
    "嗯嗯",
    "啊",
    "呃",
    "额",
    "哦",
    "喔",
}

_IGNORABLE_ASR_TEXTS = _FILLERS | {
    "转款",
    "转款了",
    "傻了",
    "你已经把",
    "已经把",
}

_HARD_STOP_WORDS = ("急停", "别动", "stop", "halt")
_SOFT_STOP_WORDS = ("停止", "停下", "停住")
_SPIN_ROUTINE = RoutineCommand(
    name="spin",
    steps=(
        MoveCommand(direction="right", duration_ms=700, speed=30),
        MoveCommand(direction="right", duration_ms=900, speed=30),
    ),
)
_DANCE_ROUTINE = RoutineCommand(
    name="dance",
    steps=(
        MoveCommand(direction="left", duration_ms=300, speed=30),
        MoveCommand(direction="right", duration_ms=300, speed=30),
        MoveCommand(direction="left", duration_ms=350, speed=30),
        MoveCommand(direction="right", duration_ms=350, speed=30),
        MoveCommand(direction="forward", duration_ms=250, speed=25),
        MoveCommand(direction="backward", duration_ms=250, speed=25),
    ),
)
_ROUTINE_KEYWORDS: tuple[tuple[RoutineCommand, tuple[str, ...]], ...] = (
    (
        _SPIN_ROUTINE,
        ("转个圈", "转圈", "转一圈", "原地转圈", "原地转一圈", "旋转一圈", "绕一圈"),
    ),
    (
        _DANCE_ROUTINE,
        ("跳舞", "跳个舞", "跳一下舞", "表演一下", "来个舞", "舞蹈"),
    ),
)
_DIRECTION_KEYWORDS: tuple[
    tuple[Literal["forward", "backward", "left", "right"], tuple[str, ...]],
    ...
] = (
    ("forward", ("向前", "往前", "前进", "朝前", "前走")),
    ("backward", ("向后", "往后", "后退", "倒车", "退后")),
    ("left", ("向左", "往左", "左转", "转左")),
    ("right", ("向右", "往右", "右转", "转右")),
)


def parse_local_command(text: str) -> LocalCommand | None:
    normalized = _normalize(text)
    if normalized in _FILLERS:
        return None
    if any(word in normalized for word in _HARD_STOP_WORDS):
        return LocalCommand(kind="stop")
    for routine, keywords in _ROUTINE_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return LocalCommand(kind="routine", routine=routine)
    for direction, keywords in _DIRECTION_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return LocalCommand(
                kind="move",
                move=MoveCommand(
                    direction=direction,
                    duration_ms=_parse_duration_ms(normalized),
                    speed=_parse_speed(normalized),
                ),
            )
    if any(word in normalized for word in _SOFT_STOP_WORDS):
        return LocalCommand(kind="stop")
    return None


def is_ignorable_voice_text(text: str) -> bool:
    return _normalize(text) in _IGNORABLE_ASR_TEXTS


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r"[\s，。！？、,.!?;；:：\"'“”‘’（）()]+", "", lowered)


def _parse_duration_ms(normalized: str) -> int:
    ms_match = re.search(r"(\d+)(?:毫秒|ms)", normalized)
    if ms_match:
        return _bounded_int(int(ms_match.group(1)), lower=100, upper=1000)

    second_match = re.search(r"(\d+)(?:秒|s)", normalized)
    if second_match:
        return _bounded_int(int(second_match.group(1)) * 1000, lower=100, upper=1000)

    return 500


def _parse_speed(normalized: str) -> int:
    match = re.search(r"(?:速度|速|speed)(\d+)", normalized)
    if not match:
        return 25
    return _bounded_int(int(match.group(1)), lower=10, upper=40)


def _bounded_int(value: int, *, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))
