"""Sensor driver — ultrasonic (HC-SR04) and infrared obstacle sensors.

GPIO pins (typical LOBOROBOT wiring):
  - Ultrasonic TRIG: GPIO 27
  - Ultrasonic ECHO: GPIO 22
  - IR Left:  GPIO 12
  - IR Right: GPIO 16
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# GPIO pin assignments
TRIG_PIN = 27
ECHO_PIN = 22
IR_LEFT_PIN = 12
IR_RIGHT_PIN = 16

MAX_DISTANCE_CM = 300.0
SPEED_OF_SOUND_CM_US = 0.0343  # cm per microsecond


class SensorDriver:
    """Sensor driver with mock fallback for non-RPi platforms."""

    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._gpio: Any = None

        if not mock:
            try:
                import RPi.GPIO as GPIO

                self._gpio = GPIO
                self._gpio.setmode(GPIO.BCM)
                self._gpio.setwarnings(False)
                self._gpio.setup(TRIG_PIN, GPIO.OUT)
                self._gpio.setup(ECHO_PIN, GPIO.IN)
                self._gpio.setup(IR_LEFT_PIN, GPIO.IN)
                self._gpio.setup(IR_RIGHT_PIN, GPIO.IN)
                self._gpio.output(TRIG_PIN, False)
                time.sleep(0.1)
                logger.info("Sensor driver initialized (hardware mode)")
            except (ImportError, OSError) as exc:
                logger.warning("Hardware not available, falling back to mock: %s", exc)
                self._mock = True
        else:
            logger.info("Sensor driver initialized (mock mode)")

    def read_ultrasonic(self) -> dict[str, Any]:
        """Read ultrasonic distance in centimeters."""
        if self._mock:
            return {"ok": True, "distance_cm": 50.0}

        try:
            # Send trigger pulse
            self._gpio.output(TRIG_PIN, True)
            time.sleep(0.00001)  # 10 microseconds
            self._gpio.output(TRIG_PIN, False)

            # Wait for echo start
            timeout_start = time.monotonic()
            pulse_start = timeout_start
            while self._gpio.input(ECHO_PIN) == 0:
                pulse_start = time.monotonic()
                if pulse_start - timeout_start > 0.04:  # 40ms timeout
                    return {"ok": False, "distance_cm": MAX_DISTANCE_CM}

            # Wait for echo end
            pulse_end = pulse_start
            while self._gpio.input(ECHO_PIN) == 1:
                pulse_end = time.monotonic()
                if pulse_end - pulse_start > 0.04:
                    return {"ok": False, "distance_cm": MAX_DISTANCE_CM}

            duration_us = (pulse_end - pulse_start) * 1_000_000
            distance_cm = (duration_us * SPEED_OF_SOUND_CM_US) / 2.0
            distance_cm = min(distance_cm, MAX_DISTANCE_CM)

            return {"ok": True, "distance_cm": round(distance_cm, 1)}

        except Exception as exc:
            logger.exception("Ultrasonic read error")
            return {"ok": False, "distance_cm": MAX_DISTANCE_CM}

    def read_infrared(self) -> dict[str, Any]:
        """Read infrared obstacle sensors. LOW = obstacle detected."""
        if self._mock:
            return {"ok": True, "left_obstacle": False, "right_obstacle": False}

        try:
            left = not self._gpio.input(IR_LEFT_PIN)   # Active LOW
            right = not self._gpio.input(IR_RIGHT_PIN)  # Active LOW
            return {"ok": True, "left_obstacle": left, "right_obstacle": right}
        except Exception as exc:
            logger.exception("Infrared read error")
            return {"ok": False, "left_obstacle": False, "right_obstacle": False}

    def cleanup(self) -> None:
        """Release GPIO resources."""
        if self._gpio and not self._mock:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
