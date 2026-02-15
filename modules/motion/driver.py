"""Motion driver — async, cancellable motor control.

Refactored from legacy/src/LOBOROBOT.py:
- Uses asyncio.sleep instead of time.sleep (cancellable)
- asyncio.Event for stop/cancel
- Graceful degradation on non-RPi platforms (mock mode)

Hardware:
- PCA9685 PWM controller on I2C bus 1, address 0x40
- 4 DC motors (quad-wheel): channels 0-8 on PCA9685 + GPIO 24/25 for Motor D
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# PCA9685 registers
PCA9685_ADDRESS = 0x40
MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06
LED0_ON_H = 0x07
LED0_OFF_L = 0x08
LED0_OFF_H = 0x09

# Motor channel mapping on PCA9685
PWMA = 0   # Motor A (left front) speed
AIN1 = 2   # Motor A direction
AIN2 = 1   # Motor A direction
PWMB = 5   # Motor B (right front) speed
BIN1 = 3   # Motor B direction
BIN2 = 4   # Motor B direction
PWMC = 6   # Motor C (left rear) speed
CIN1 = 8   # Motor C direction
CIN2 = 7   # Motor C direction
PWMD = 11  # Motor D (right rear) speed

# GPIO pins for Motor D direction
DIN1_PIN = 25
DIN2_PIN = 24


class MotionDriver:
    """Async motor driver with cancel support."""

    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._bus: Any = None
        self._gpio: Any = None
        self._cancel_event = asyncio.Event()
        self._stopped = False

        if not mock:
            try:
                import smbus2
                import RPi.GPIO as GPIO

                self._bus = smbus2.SMBus(1)
                self._gpio = GPIO
                self._gpio.setmode(GPIO.BCM)
                self._gpio.setwarnings(False)
                self._gpio.setup(DIN1_PIN, GPIO.OUT)
                self._gpio.setup(DIN2_PIN, GPIO.OUT)
                self._init_pca9685()
                logger.info("Motion driver initialized (hardware mode)")
            except (ImportError, OSError) as exc:
                logger.warning("Hardware not available, falling back to mock: %s", exc)
                self._mock = True
        else:
            logger.info("Motion driver initialized (mock mode)")

    def _init_pca9685(self) -> None:
        """Initialize PCA9685 with 50Hz PWM frequency."""
        if not self._bus:
            return
        self._bus.write_byte_data(PCA9685_ADDRESS, MODE1, 0x00)
        time.sleep(0.005)
        # Set prescale for 50Hz
        prescale = int(25000000.0 / (4096 * 50.0) - 1)
        old_mode = self._bus.read_byte_data(PCA9685_ADDRESS, MODE1)
        self._bus.write_byte_data(PCA9685_ADDRESS, MODE1, (old_mode & 0x7F) | 0x10)
        self._bus.write_byte_data(PCA9685_ADDRESS, PRESCALE, prescale)
        self._bus.write_byte_data(PCA9685_ADDRESS, MODE1, old_mode)
        time.sleep(0.005)
        self._bus.write_byte_data(PCA9685_ADDRESS, MODE1, old_mode | 0xA0)

    def _set_pwm(self, channel: int, on: int, off: int) -> None:
        """Set PWM on a PCA9685 channel."""
        if self._mock:
            return
        base = LED0_ON_L + 4 * channel
        self._bus.write_byte_data(PCA9685_ADDRESS, base, on & 0xFF)
        self._bus.write_byte_data(PCA9685_ADDRESS, base + 1, on >> 8)
        self._bus.write_byte_data(PCA9685_ADDRESS, base + 2, off & 0xFF)
        self._bus.write_byte_data(PCA9685_ADDRESS, base + 3, off >> 8)

    def _set_motor_speed(self, channel: int, speed: int) -> None:
        """Set motor speed (0-100) on a PWM channel."""
        duty = max(0, min(4095, int(speed * 4095 / 100)))
        self._set_pwm(channel, 0, duty)

    def _set_digital(self, channel: int, value: bool) -> None:
        """Set a PCA9685 channel to full on or off (digital mode)."""
        if value:
            self._set_pwm(channel, 4096, 0)
        else:
            self._set_pwm(channel, 0, 0)

    def _set_gpio(self, pin: int, value: bool) -> None:
        """Set a RPi GPIO pin."""
        if self._mock:
            return
        self._gpio.output(pin, value)

    def _set_motor(
        self, pwm_ch: int, dir1: int | None, dir2: int | None,
        gpio1: int | None, gpio2: int | None,
        speed: int, forward: bool
    ) -> None:
        """Configure a single motor direction and speed."""
        if dir1 is not None and dir2 is not None:
            self._set_digital(dir1, forward)
            self._set_digital(dir2, not forward)
        if gpio1 is not None and gpio2 is not None:
            self._set_gpio(gpio1, forward)
            self._set_gpio(gpio2, not forward)
        self._set_motor_speed(pwm_ch, speed)

    def _motors_forward(self, speed: int) -> None:
        self._set_motor(PWMA, AIN1, AIN2, None, None, speed, True)
        self._set_motor(PWMB, BIN1, BIN2, None, None, speed, True)
        self._set_motor(PWMC, CIN1, CIN2, None, None, speed, True)
        self._set_motor(PWMD, None, None, DIN1_PIN, DIN2_PIN, speed, True)

    def _motors_backward(self, speed: int) -> None:
        self._set_motor(PWMA, AIN1, AIN2, None, None, speed, False)
        self._set_motor(PWMB, BIN1, BIN2, None, None, speed, False)
        self._set_motor(PWMC, CIN1, CIN2, None, None, speed, False)
        self._set_motor(PWMD, None, None, DIN1_PIN, DIN2_PIN, speed, False)

    def _motors_turn_left(self, speed: int) -> None:
        self._set_motor(PWMA, AIN1, AIN2, None, None, speed, False)
        self._set_motor(PWMB, BIN1, BIN2, None, None, speed, True)
        self._set_motor(PWMC, CIN1, CIN2, None, None, speed, False)
        self._set_motor(PWMD, None, None, DIN1_PIN, DIN2_PIN, speed, True)

    def _motors_turn_right(self, speed: int) -> None:
        self._set_motor(PWMA, AIN1, AIN2, None, None, speed, True)
        self._set_motor(PWMB, BIN1, BIN2, None, None, speed, False)
        self._set_motor(PWMC, CIN1, CIN2, None, None, speed, True)
        self._set_motor(PWMD, None, None, DIN1_PIN, DIN2_PIN, speed, False)

    def _motors_stop(self) -> None:
        for ch in [PWMA, PWMB, PWMC, PWMD]:
            self._set_motor_speed(ch, 0)

    # ─── Public async API ────────────────────────────────────

    async def forward(self, speed: int, duration_ms: int) -> dict[str, Any]:
        return await self._timed_motion("forward", self._motors_forward, speed, duration_ms)

    async def backward(self, speed: int, duration_ms: int) -> dict[str, Any]:
        return await self._timed_motion("backward", self._motors_backward, speed, duration_ms)

    async def turn_left(self, speed: int, duration_ms: int) -> dict[str, Any]:
        return await self._timed_motion("turn_left", self._motors_turn_left, speed, duration_ms)

    async def turn_right(self, speed: int, duration_ms: int) -> dict[str, Any]:
        return await self._timed_motion("turn_right", self._motors_turn_right, speed, duration_ms)

    async def stop(self) -> dict[str, Any]:
        self._cancel_event.set()
        self._motors_stop()
        logger.info("Motors stopped")
        return {"ok": True}

    def reset_cancel(self) -> None:
        """Reset cancel event for the next motion command."""
        self._cancel_event.clear()

    async def _timed_motion(
        self,
        action: str,
        motor_fn: Any,
        speed: int,
        duration_ms: int,
    ) -> dict[str, Any]:
        """Execute a timed motion command, cancellable via cancel_event."""
        self.reset_cancel()
        speed = max(0, min(100, speed))
        duration_ms = max(0, min(10000, duration_ms))

        logger.info("Motion %s: speed=%d duration=%dms", action, speed, duration_ms)
        motor_fn(speed)

        start = time.monotonic()
        try:
            await asyncio.wait_for(
                self._cancel_event.wait(),
                timeout=duration_ms / 1000.0,
            )
            # Cancelled
            self._motors_stop()
            elapsed = int((time.monotonic() - start) * 1000)
            logger.info("Motion %s cancelled after %dms", action, elapsed)
            return {"ok": False, "actual_duration_ms": elapsed, "cancelled": True}
        except asyncio.TimeoutError:
            # Normal completion
            self._motors_stop()
            elapsed = int((time.monotonic() - start) * 1000)
            logger.info("Motion %s completed in %dms", action, elapsed)
            return {"ok": True, "actual_duration_ms": elapsed}

    def cleanup(self) -> None:
        """Release hardware resources."""
        self._motors_stop()
        if self._gpio and not self._mock:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
        if self._bus and not self._mock:
            try:
                self._bus.close()
            except Exception:
                pass
