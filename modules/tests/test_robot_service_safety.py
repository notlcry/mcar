"""Tests for the Python Robot Service safety boundary."""

from __future__ import annotations

import pytest

from robot_service.service import create_robot_service


@pytest.fixture
def service():
    return create_robot_service(mock=True)


@pytest.mark.asyncio
async def test_motion_forward_is_blocked_when_obstacle_is_present(service) -> None:
    service.state.set("obstacle", True)

    result = await service.invoke(
        "tool.motion.forward",
        {"speed": 30, "duration_ms": 100},
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "E_STATE_OBSTACLE"


@pytest.mark.asyncio
async def test_motion_schema_bounds_are_enforced_before_driver_call(service) -> None:
    result = await service.invoke(
        "tool.motion.forward",
        {"speed": 30, "duration_ms": 6000},
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "E_INPUT_SCHEMA"


@pytest.mark.asyncio
async def test_kid_mode_caps_motion_speed(service) -> None:
    service.state.set_mode("kid")

    result = await service.invoke(
        "tool.motion.forward",
        {"speed": 40, "duration_ms": 100},
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "E_POLICY_ROLE_DENIED"
    assert "30" in result.error.message


@pytest.mark.asyncio
async def test_emergency_stop_blocks_motion_but_allows_read_only_status(service) -> None:
    await service.trigger_stop("test")

    motion_result = await service.invoke(
        "tool.motion.forward",
        {"speed": 20, "duration_ms": 100},
    )
    status_result = await service.invoke("tool.mock.status", {})

    assert motion_result.success is False
    assert motion_result.error is not None
    assert motion_result.error.code == "E_STATE_ESTOP"
    assert status_result.success is True


@pytest.mark.asyncio
async def test_emergency_stop_does_not_teardown_sensor_or_button_gpio(service) -> None:
    def fail_cleanup() -> None:
        raise AssertionError("cleanup should not run during emergency stop")

    service.modules.sensor.driver.cleanup = fail_cleanup
    service.modules.button.driver.cleanup = fail_cleanup

    await service.trigger_stop("test")

    assert service.state.estop_locked is True


@pytest.mark.asyncio
async def test_sensor_reads_update_obstacle_state(service) -> None:
    service.modules.sensor.set_infrared(left_obstacle=True, right_obstacle=False)

    result = await service.invoke("tool.sensor.infrared", {})

    assert result.success is True
    assert service.state.get("obstacle") is True
