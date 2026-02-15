"""Tests for the Display module capabilities (mock mode)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from display.driver import DisplayDriver, VALID_EXPRESSIONS
from display.module import DisplayModule


@pytest.fixture
def display_driver() -> DisplayDriver:
    """Create a DisplayDriver in mock mode."""
    return DisplayDriver(mock=True)


@pytest.fixture
def display_module() -> DisplayModule:
    """Create a DisplayModule without starting IPC."""
    m = DisplayModule.__new__(DisplayModule)
    m._driver = DisplayDriver(mock=True)
    return m


class TestDisplayModuleManifest:
    def test_manifest(self, display_module: DisplayModule) -> None:
        manifest = display_module.manifest()
        assert manifest["module_id"] == "display"
        assert "tool.display.show_expression" in manifest["capabilities"]
        assert "tool.display.show_text" in manifest["capabilities"]
        assert "tool.display.clear" in manifest["capabilities"]

    def test_capabilities(self, display_module: DisplayModule) -> None:
        caps = display_module.capabilities()
        assert len(caps) == 3
        cap_ids = [c["capability_id"] for c in caps]
        assert "tool.display.show_expression" in cap_ids
        assert "tool.display.show_text" in cap_ids
        assert "tool.display.clear" in cap_ids


class TestDisplayDriverExpression:
    def test_show_expression_happy(self, display_driver: DisplayDriver) -> None:
        result = display_driver.show_expression("happy")
        assert result["ok"] is True
        assert result["expression"] == "happy"

    def test_show_all_expressions(self, display_driver: DisplayDriver) -> None:
        for expr in VALID_EXPRESSIONS:
            result = display_driver.show_expression(expr)
            assert result["ok"] is True
            assert result["expression"] == expr

    def test_show_invalid_expression(self, display_driver: DisplayDriver) -> None:
        result = display_driver.show_expression("angry")
        assert result["ok"] is False
        assert "error" in result


class TestDisplayDriverText:
    def test_show_text(self, display_driver: DisplayDriver) -> None:
        result = display_driver.show_text("Hello World")
        assert result["ok"] is True
        assert result["lines_shown"] >= 1

    def test_show_long_text(self, display_driver: DisplayDriver) -> None:
        long_text = "This is a very long text that should be wrapped into multiple lines on the display."
        result = display_driver.show_text(long_text)
        assert result["ok"] is True
        assert result["lines_shown"] >= 2

    def test_show_multiline_text(self, display_driver: DisplayDriver) -> None:
        text = "Line 1\nLine 2\nLine 3"
        result = display_driver.show_text(text)
        assert result["ok"] is True
        assert result["lines_shown"] == 3


class TestDisplayDriverClear:
    def test_clear(self, display_driver: DisplayDriver) -> None:
        result = display_driver.clear()
        assert result["ok"] is True


class TestDisplayDriverTextWrap:
    def test_wrap_short_text(self) -> None:
        lines = DisplayDriver._wrap_text("hello", max_chars=21)
        assert lines == ["hello"]

    def test_wrap_long_text(self) -> None:
        text = "This is a long text that needs wrapping"
        lines = DisplayDriver._wrap_text(text, max_chars=15)
        assert len(lines) >= 2
        assert all(len(line) <= 15 for line in lines)

    def test_wrap_empty_text(self) -> None:
        lines = DisplayDriver._wrap_text("", max_chars=21)
        assert lines == [""]


class TestDisplayModuleInvoke:
    @pytest.mark.asyncio
    async def test_invoke_show_expression(self, display_module: DisplayModule) -> None:
        result = await display_module.invoke(
            "tool.display.show_expression", {"expression": "thinking"}, {}
        )
        assert result["ok"] is True
        assert result["expression"] == "thinking"

    @pytest.mark.asyncio
    async def test_invoke_show_text(self, display_module: DisplayModule) -> None:
        result = await display_module.invoke(
            "tool.display.show_text", {"text": "Hello mcar!"}, {}
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_clear(self, display_module: DisplayModule) -> None:
        result = await display_module.invoke("tool.display.clear", {}, {})
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_unknown(self, display_module: DisplayModule) -> None:
        with pytest.raises(ValueError, match="Unknown capability"):
            await display_module.invoke("tool.display.nonexistent", {}, {})
