"""Button driver — GPIO-based physical emergency stop button.

Hardware: Any normally-open push button connected to a GPIO pin (default BCM17)
with internal pull-up resistor. Press pulls pin LOW (FALLING edge).

Falls back to mock mode when RPi.GPIO is not available.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ButtonDriver:
    """GPIO button driver with interrupt-based detection."""

    def __init__(
        self,
        gpio_pin: int = 17,
        debounce_ms: int = 200,
        mock: bool = False,
    ) -> None:
        self.gpio_pin = gpio_pin
        self.debounce_ms = debounce_ms
        self.gpio_available = False
        self._pressed = False
        self._callback: Callable[[], None] | None = None
        self._lock = threading.Lock()
        self._mock = mock

        if not mock:
            self._setup_gpio()
        else:
            logger.info("Button driver initialized (mock mode)")

    def _setup_gpio(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                self.gpio_pin,
                GPIO.FALLING,
                callback=self._on_press,
                bouncetime=self.debounce_ms,
            )
            self.gpio_available = True
            logger.info(
                "Button driver initialized on GPIO%d (hardware mode)",
                self.gpio_pin,
            )
        except (ImportError, RuntimeError) as exc:
            logger.warning(
                "GPIO not available, button in mock mode: %s", exc
            )
            self._mock = True

    def _on_press(self, channel: int) -> None:
        """GPIO interrupt callback."""
        with self._lock:
            self._pressed = True
        logger.info("Physical button pressed on GPIO%d", self.gpio_pin)
        if self._callback:
            self._callback()

    def on_press(self, callback: Callable[[], None]) -> None:
        """Register a callback for button press events."""
        self._callback = callback

    def is_pressed(self) -> bool:
        """Check and reset the pressed state (edge-triggered)."""
        with self._lock:
            pressed = self._pressed
            self._pressed = False
        return pressed

    def simulate_press(self) -> None:
        """Simulate a button press (for testing/mock mode)."""
        self._on_press(self.gpio_pin)

    def cleanup(self) -> None:
        """Release GPIO resources."""
        if self.gpio_available:
            try:
                import RPi.GPIO as GPIO  # type: ignore

                GPIO.remove_event_detect(self.gpio_pin)
                GPIO.cleanup(self.gpio_pin)
            except Exception:
                pass
        logger.info("Button driver cleaned up")
