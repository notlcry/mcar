"""Tests for local voice command parsing."""

from __future__ import annotations

from robot_service.command_parser import is_ignorable_voice_text, parse_local_command


def test_parse_forward_motion_command() -> None:
    command = parse_local_command("向前走一点")

    assert command is not None
    assert command.kind == "move"
    assert command.move is not None
    assert command.move.direction == "forward"
    assert command.move.duration_ms == 500
    assert command.move.speed == 25


def test_parse_timed_motion_with_then_stop_suffix() -> None:
    command = parse_local_command("向前走100毫秒，速度10，然后停止")

    assert command is not None
    assert command.kind == "move"
    assert command.move is not None
    assert command.move.direction == "forward"
    assert command.move.duration_ms == 100
    assert command.move.speed == 10


def test_parse_turn_and_stop_commands() -> None:
    left = parse_local_command("向左转")
    stop = parse_local_command("别动，停止")

    assert left is not None
    assert left.kind == "move"
    assert left.move is not None
    assert left.move.direction == "left"
    assert stop is not None
    assert stop.kind == "stop"


def test_parse_spin_and_dance_routines() -> None:
    spin = parse_local_command("转个圈")
    dance = parse_local_command("跳个舞")

    assert spin is not None
    assert spin.kind == "routine"
    assert spin.routine is not None
    assert spin.routine.name == "spin"
    assert len(spin.routine.steps) >= 1
    assert dance is not None
    assert dance.kind == "routine"
    assert dance.routine is not None
    assert dance.routine.name == "dance"
    assert len(dance.routine.steps) > 1


def test_ignores_fillers_and_non_commands() -> None:
    assert parse_local_command("嗯。") is None
    assert parse_local_command("看一下状态") is None


def test_identifies_known_asr_noise_texts() -> None:
    assert is_ignorable_voice_text("转款。") is True
    assert is_ignorable_voice_text("傻了。") is True
    assert is_ignorable_voice_text("你已经把。") is True
    assert is_ignorable_voice_text("看一下状态") is False
    assert is_ignorable_voice_text("向前走一点") is False
