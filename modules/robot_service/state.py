"""State service for robot policy decisions and API status."""

from __future__ import annotations

import time
from typing import Any

from .models import Mode, StateSnapshot


class RobotState:
    def __init__(self, estop_cooldown_ms: int = 2000) -> None:
        self._values: dict[str, Any] = {
            "session": "IDLE",
            "mode": "normal",
            "apiStatus": "online",
            "obstacle": False,
            "battery": 1.0,
        }
        self._estop_cooldown_ms = estop_cooldown_ms
        self._estop_until = 0.0
        self._speed_limits: dict[Mode, int] = {
            "normal": 100,
            "safety": 50,
            "kid": 30,
            "debug": 100,
            "mute": 100,
        }

    def get(self, key: str) -> Any:
        if key == "estop":
            return self.estop_locked
        return self._values.get(key)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def get_mode(self) -> Mode:
        return self._values["mode"]

    def set_mode(self, mode: Mode) -> None:
        self._values["mode"] = mode

    def get_max_speed(self) -> int:
        return self._speed_limits[self.get_mode()]

    @property
    def estop_locked(self) -> bool:
        return time.monotonic() < self._estop_until

    def estop_remaining_ms(self) -> int:
        remaining = self._estop_until - time.monotonic()
        return max(0, int(remaining * 1000))

    def lock_estop(self) -> None:
        self._estop_until = time.monotonic() + self._estop_cooldown_ms / 1000

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            session=self._values["session"],
            mode=self.get_mode(),
            apiStatus=self._values["apiStatus"],
            obstacle=bool(self._values["obstacle"]),
            battery=float(self._values["battery"]),
            estopLocked=self.estop_locked,
            maxSpeed=self.get_max_speed(),
        )
