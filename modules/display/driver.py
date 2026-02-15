"""Display driver — SSD1306 OLED 128x64 I2C.

Hardware: SSD1306 OLED display on I2C bus 1
Uses PIL/Pillow for drawing text and expressions.
Mock fallback mode for CI / non-RPi environments.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

VALID_EXPRESSIONS = frozenset({
    "happy", "sad", "thinking", "confused", "excited",
    "sleeping", "listening", "speaking", "neutral",
})

# Simple pixel art for expressions (drawn as text fallback)
EXPRESSION_ART: dict[str, list[str]] = {
    "happy":     ["  ^  ^  ", " (^_^) ", "  \\__/  "],
    "sad":       ["  .  .  ", " (T_T) ", "  /--\\  "],
    "thinking":  ["  ?  ?  ", " (o_o) ", "  ----  "],
    "confused":  ["  @  @  ", " (o_O) ", "  ~--~  "],
    "excited":   ["  *  *  ", " (>w<) ", "  \\!!/ "],
    "sleeping":  ["  -  -  ", " (-_-) ", "  zZz   "],
    "listening": ["  o  o  ", " (o_o) ", "  |__|  "],
    "speaking":  ["  ^  ^  ", " (^o^) ", "  )__(  "],
    "neutral":   ["  .  .  ", " (-_-) ", "  ----  "],
}


class DisplayDriver:
    """Async OLED display driver with mock fallback."""

    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._device: Any = None
        self._font: Any = None
        self._current_expression: str = "neutral"

        if not mock:
            try:
                self._init_hardware()
            except (ImportError, OSError) as exc:
                logger.warning("Display hardware not available, falling back to mock: %s", exc)
                self._mock = True
        else:
            logger.info("Display driver initialized (mock mode)")

    def _init_hardware(self) -> None:
        """Initialize SSD1306 OLED display."""
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306

        serial = i2c(port=1, address=0x3C)
        self._device = ssd1306(serial, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        self._device.contrast(200)

        # Load default font
        try:
            from PIL import ImageFont
            self._font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 12)
        except Exception:
            from PIL import ImageFont
            self._font = ImageFont.load_default()

        logger.info("Display driver initialized (hardware mode)")

    def show_expression(self, expression: str) -> dict[str, Any]:
        """Display an expression on the OLED screen."""
        if expression not in VALID_EXPRESSIONS:
            return {"ok": False, "error": f"Invalid expression: {expression}"}

        self._current_expression = expression

        if self._mock:
            art = EXPRESSION_ART.get(expression, EXPRESSION_ART["neutral"])
            logger.info("Mock display expression [%s]:\n%s", expression, "\n".join(art))
            return {"ok": True, "expression": expression}

        try:
            from PIL import Image, ImageDraw

            image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 0)
            draw = ImageDraw.Draw(image)

            art = EXPRESSION_ART.get(expression, EXPRESSION_ART["neutral"])
            y_start = (DISPLAY_HEIGHT - len(art) * 16) // 2
            for i, line in enumerate(art):
                x = (DISPLAY_WIDTH - len(line) * 8) // 2
                draw.text((max(0, x), y_start + i * 16), line, fill=1, font=self._font)

            # Label at bottom
            draw.text((2, DISPLAY_HEIGHT - 12), expression, fill=1, font=self._font)

            self._device.display(image)
            return {"ok": True, "expression": expression}

        except Exception as exc:
            logger.error("Display expression error: %s", exc)
            return {"ok": False, "error": str(exc)}

    def show_text(self, text: str, font_size: int = 12) -> dict[str, Any]:
        """Display text on the OLED screen."""
        if self._mock:
            lines = self._wrap_text(text, max_chars=21)
            logger.info("Mock display text:\n%s", "\n".join(lines[:4]))
            return {"ok": True, "lines_shown": min(len(lines), 4)}

        try:
            from PIL import Image, ImageDraw, ImageFont

            # Load font at requested size
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", font_size
                )
            except Exception:
                font = ImageFont.load_default()

            image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 0)
            draw = ImageDraw.Draw(image)

            max_chars = DISPLAY_WIDTH // (font_size // 2 + 1)
            lines = self._wrap_text(text, max_chars=max(10, max_chars))
            max_lines = min(4, DISPLAY_HEIGHT // (font_size + 2))

            for i, line in enumerate(lines[:max_lines]):
                draw.text((2, 2 + i * (font_size + 2)), line, fill=1, font=font)

            self._device.display(image)
            return {"ok": True, "lines_shown": min(len(lines), max_lines)}

        except Exception as exc:
            logger.error("Display text error: %s", exc)
            return {"ok": False, "error": str(exc)}

    def clear(self) -> dict[str, Any]:
        """Clear the display."""
        if self._mock:
            logger.info("Mock display cleared")
            return {"ok": True}

        try:
            from PIL import Image
            image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 0)
            self._device.display(image)
            return {"ok": True}
        except Exception as exc:
            logger.error("Display clear error: %s", exc)
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _wrap_text(text: str, max_chars: int = 21) -> list[str]:
        """Wrap text into lines of max_chars width."""
        lines: list[str] = []
        for paragraph in text.split("\n"):
            if not paragraph:
                lines.append("")
                continue
            while len(paragraph) > max_chars:
                # Find a good break point
                break_at = paragraph.rfind(" ", 0, max_chars)
                if break_at <= 0:
                    break_at = max_chars
                lines.append(paragraph[:break_at])
                paragraph = paragraph[break_at:].lstrip()
            if paragraph:
                lines.append(paragraph)
        return lines

    def cleanup(self) -> None:
        """Release hardware resources."""
        if not self._mock and self._device:
            try:
                self._device.hide()
            except Exception:
                pass
