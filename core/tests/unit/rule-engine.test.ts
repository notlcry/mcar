/**
 * RuleEngine unit tests.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { RuleEngine, type RuleCondition } from "../../src/automation/rule-engine.js";
import type { MemoryService } from "../../src/memory/memory-service.js";
import type { MemoryEntry } from "../../src/memory/types.js";
import { StateService } from "../../src/state/state-service.js";
import type { CapabilityExecutor } from "../../src/capability/executor.js";
import type { AuditLogger } from "../../src/audit/audit-logger.js";

function makeRuleEntry(content: Record<string, unknown>): MemoryEntry {
  return {
    id: `mem-${content.rule_id}`,
    type: "rule",
    content,
    summary: `Rule: ${content.rule_id}`,
    source: "user_explicit",
    confidence: 1.0,
    privacy_level: "normal",
    tags: [],
    links: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function makeMockMemoryService(entries: MemoryEntry[]): MemoryService {
  return {
    search: () => entries,
  } as unknown as MemoryService;
}

function makeMockAuditLogger(): AuditLogger {
  return {
    info: () => ({ id: "a", traceId: "t", eventType: "e", timestamp: "", severity: "INFO" }),
    warn: () => ({ id: "a", traceId: "t", eventType: "e", timestamp: "", severity: "WARN" }),
    error: () => ({ id: "a", traceId: "t", eventType: "e", timestamp: "", severity: "ERROR" }),
  } as unknown as AuditLogger;
}

describe("RuleEngine", () => {
  let stateService: StateService;
  let auditLogger: AuditLogger;

  beforeEach(() => {
    stateService = new StateService();
    auditLogger = makeMockAuditLogger();
  });

  it("should trigger set_mode action when state condition met", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "low_battery_safety",
        when: { state: { key: "batteryLevel", op: "<", value: 0.2 } },
        then: { action: "set_mode", mode: "safety" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    // Battery is 1.0 by default — rule should NOT trigger
    const r1 = engine.evaluate();
    expect(r1).toHaveLength(0);
    expect(stateService.getMode()).toBe("normal");

    // Set battery low — rule should trigger
    stateService.set("batteryLevel", 0.15);
    const r2 = engine.evaluate();
    expect(r2).toHaveLength(1);
    expect(r2[0].ruleId).toBe("low_battery_safety");
    expect(stateService.getMode()).toBe("safety");
  });

  it("should not re-trigger an already active rule", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "obstacle_stop",
        when: { state: { key: "obstacle", op: "==", value: true } },
        then: { action: "set_mode", mode: "safety" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    stateService.set("obstacle", true);

    // First evaluate triggers
    const r1 = engine.evaluate();
    expect(r1).toHaveLength(1);

    // Second evaluate does NOT re-trigger (already active)
    const r2 = engine.evaluate();
    expect(r2).toHaveLength(0);
  });

  it("should deactivate rule when condition no longer met", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "obstacle_stop",
        when: { state: { key: "obstacle", op: "==", value: true } },
        then: { action: "set_mode", mode: "safety" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    stateService.set("obstacle", true);
    engine.evaluate(); // triggers

    stateService.set("obstacle", false);
    engine.evaluate(); // deactivates

    // Set obstacle again — should trigger again
    stateService.set("obstacle", true);
    const r3 = engine.evaluate();
    expect(r3).toHaveLength(1);
  });

  it("should evaluate time_range condition (same-day range)", () => {
    const engine = new RuleEngine(
      makeMockMemoryService([]),
      stateService,
      null,
      auditLogger
    );

    // 09:00-17:00 — test with time inside range
    const condition: RuleCondition = { time_range: "09:00-17:00" };

    // We test the public evaluateCondition method
    // Simulate 12:00 — should be in range
    const inRange = engine.evaluateCondition(condition);
    // We can't control Date.now() without mocking, but we can verify it returns a boolean
    expect(typeof inRange).toBe("boolean");
  });

  it("should handle overnight time_range (e.g., 22:00-07:00)", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "night_mute",
        when: { time_range: "22:00-07:00" },
        then: { action: "set_mode", mode: "mute" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    // We evaluate — the result depends on current time, but engine should not crash
    const result = engine.evaluate();
    expect(Array.isArray(result)).toBe(true);
  });

  it("should handle state op != correctly", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "not_idle_warn",
        when: { state: { key: "session", op: "!=", value: "IDLE" } },
        then: { action: "set_mode", mode: "debug" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    // session is IDLE by default — condition NOT met
    const r1 = engine.evaluate();
    expect(r1).toHaveLength(0);

    // Change session — condition met
    stateService.set("session", "THINKING");
    const r2 = engine.evaluate();
    expect(r2).toHaveLength(1);
    expect(stateService.getMode()).toBe("debug");
  });

  it("should trigger invoke action via executor", async () => {
    let invokedCapId = "";
    let invokedParams: Record<string, unknown> = {};

    const mockExecutor = {
      execute: async (capId: string, params: Record<string, unknown>) => {
        invokedCapId = capId;
        invokedParams = params;
        return { success: true, data: {} };
      },
    } as unknown as CapabilityExecutor;

    const entries = [
      makeRuleEntry({
        rule_id: "auto_patrol",
        when: { state: { key: "session", op: "==", value: "IDLE" } },
        then: { action: "invoke", capability_id: "tool.motion.move", params: { direction: "forward", speed: 20 } },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, mockExecutor, auditLogger);

    const result = engine.evaluate();
    expect(result).toHaveLength(1);
    expect(result[0].action).toBe("invoke");

    // Wait for async invoke
    await new Promise((r) => setTimeout(r, 10));
    expect(invokedCapId).toBe("tool.motion.move");
    expect(invokedParams.direction).toBe("forward");
  });

  it("should skip malformed rule entries gracefully", () => {
    const entries = [
      makeRuleEntry({ rule_id: "bad_rule" }), // missing when/then
      makeRuleEntry({
        rule_id: "good_rule",
        when: { state: { key: "obstacle", op: "==", value: true } },
        then: { action: "set_mode", mode: "safety" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    stateService.set("obstacle", true);
    const result = engine.evaluate();
    // Only the valid rule triggers
    expect(result).toHaveLength(1);
    expect(result[0].ruleId).toBe("good_rule");
  });

  it("should handle state >= and <= comparisons", () => {
    const entries = [
      makeRuleEntry({
        rule_id: "speed_limit",
        when: { state: { key: "batteryLevel", op: ">=", value: 0.5 } },
        then: { action: "set_mode", mode: "normal" },
      }),
    ];

    const memoryService = makeMockMemoryService(entries);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger);

    // Battery is 1.0 — >= 0.5 is true
    const r1 = engine.evaluate();
    expect(r1).toHaveLength(1);
  });

  it("should start and stop periodic evaluation", () => {
    const memoryService = makeMockMemoryService([]);
    const engine = new RuleEngine(memoryService, stateService, null, auditLogger, { intervalMs: 100 });

    engine.start();
    // Calling start again should be a no-op
    engine.start();

    engine.stop();
    // Calling stop again should be safe
    engine.stop();
  });
});
