"""Memory-backed automation rules for Robot Service."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class RuleEngine:
    def __init__(self, service: Any) -> None:
        self._service = service
        self._active_rules: set[str] = set()

    async def evaluate(self) -> list[dict[str, str]]:
        triggered: list[dict[str, str]] = []
        rules = self._service.memory.search(types=["rule"], include_private=True, limit=100)
        for entry in rules:
            content = entry.get("content") or {}
            rule_id = content.get("rule_id")
            when = content.get("when")
            then = content.get("then")
            if not rule_id or not when or not then:
                continue

            if self._condition_met(when) and rule_id not in self._active_rules:
                self._active_rules.add(rule_id)
                await self._trigger(rule_id, then)
                triggered.append({"ruleId": rule_id, "action": then["action"]})
            elif not self._condition_met(when):
                self._active_rules.discard(rule_id)
        return triggered

    def _condition_met(self, when: dict[str, Any]) -> bool:
        time_range = when.get("time_range")
        if time_range and not self._time_range_matches(time_range):
            return False
        state = when.get("state")
        if state and not self._state_matches(state):
            return False
        return True

    def _state_matches(self, state: dict[str, Any]) -> bool:
        actual = self._service.state.get(state["key"])
        expected = state.get("value")
        op = state.get("op")
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        if op == ">":
            return actual > expected
        if op == ">=":
            return actual >= expected
        if op == "<":
            return actual < expected
        if op == "<=":
            return actual <= expected
        return False

    def _time_range_matches(self, time_range: str) -> bool:
        start, end = time_range.split("-", 1)
        start_minutes = self._parse_minutes(start)
        end_minutes = self._parse_minutes(end)
        now = datetime.now()
        current = now.hour * 60 + now.minute
        if start_minutes > end_minutes:
            return current >= start_minutes or current < end_minutes
        return start_minutes <= current < end_minutes

    def _parse_minutes(self, value: str) -> int:
        hour, minute = value.split(":", 1)
        return int(hour) * 60 + int(minute)

    async def _trigger(self, rule_id: str, action: dict[str, Any]) -> None:
        if action["action"] == "set_mode":
            self._service.set_mode(action["mode"])
        if action["action"] == "invoke":
            await self._service.invoke(action["capability_id"], action.get("params") or {})
        self._service.audit("rule.triggered", {"rule_id": rule_id, "action": action["action"]})
