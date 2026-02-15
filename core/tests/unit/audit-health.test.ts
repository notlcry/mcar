/**
 * Audit persistence and health monitoring tests.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { AuditLogger } from "../../src/audit/audit-logger.js";
import { AuditStore } from "../../src/audit/audit-store.js";
import { HealthMonitor } from "../../src/health/health-monitor.js";
import { StateService } from "../../src/state/state-service.js";

// ─── AuditStore tests ────────────────────────────────────────

describe("AuditStore", () => {
  let store: AuditStore;

  beforeEach(() => {
    store = new AuditStore(":memory:");
  });

  afterEach(() => {
    store.close();
  });

  it("should save and retrieve events", () => {
    store.save({
      id: "evt1",
      traceId: "trace1",
      eventType: "test.event",
      timestamp: new Date().toISOString(),
      payload: { key: "value" },
      severity: "INFO",
    });

    const events = store.getRecent(10);
    expect(events).toHaveLength(1);
    expect(events[0].id).toBe("evt1");
    expect(events[0].payload?.key).toBe("value");
  });

  it("should retrieve by trace ID", () => {
    store.save({
      id: "evt1",
      traceId: "trace-A",
      eventType: "start",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });
    store.save({
      id: "evt2",
      traceId: "trace-A",
      eventType: "end",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });
    store.save({
      id: "evt3",
      traceId: "trace-B",
      eventType: "other",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });

    const traceA = store.getByTraceId("trace-A");
    expect(traceA).toHaveLength(2);
  });

  it("should retrieve by event type", () => {
    store.save({
      id: "evt1",
      traceId: "t1",
      eventType: "tool.invoke",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });
    store.save({
      id: "evt2",
      traceId: "t2",
      eventType: "tool.invoke",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });

    const events = store.getByEventType("tool.invoke");
    expect(events).toHaveLength(2);
  });

  it("should count events", () => {
    store.save({ id: "a", traceId: "t", eventType: "x", timestamp: new Date().toISOString(), severity: "INFO" });
    store.save({ id: "b", traceId: "t", eventType: "y", timestamp: new Date().toISOString(), severity: "INFO" });
    expect(store.count()).toBe(2);
  });

  it("should export all events", () => {
    store.save({ id: "a", traceId: "t", eventType: "x", timestamp: new Date().toISOString(), severity: "INFO" });
    const all = store.exportAll();
    expect(all).toHaveLength(1);
  });

  it("should ignore duplicate IDs", () => {
    const event = {
      id: "dup",
      traceId: "t",
      eventType: "x",
      timestamp: new Date().toISOString(),
      severity: "INFO" as const,
    };
    store.save(event);
    store.save(event); // Should not throw
    expect(store.count()).toBe(1);
  });
});

// ─── AuditLogger + Store integration ─────────────────────────

describe("AuditLogger with Store", () => {
  let logger: AuditLogger;
  let store: AuditStore;

  beforeEach(() => {
    store = new AuditStore(":memory:");
    logger = new AuditLogger();
    logger.setStore(store);
  });

  afterEach(() => {
    store.close();
  });

  it("should persist events to store", () => {
    logger.info("trace1", "test.event", { data: "hello" });
    logger.warn("trace1", "test.warning");
    logger.error("trace2", "test.error");

    // Check in-memory buffer
    expect(logger.getRecent(10)).toHaveLength(3);

    // Check persistent store
    expect(store.count()).toBe(3);
    const events = store.getRecent(10);
    expect(events).toHaveLength(3);
  });

  it("should persist with correct severity", () => {
    logger.info("t", "info.event");
    logger.warn("t", "warn.event");
    logger.error("t", "error.event");

    const events = store.getRecent(10);
    const severities = events.map((e) => e.severity);
    expect(severities).toContain("INFO");
    expect(severities).toContain("WARN");
    expect(severities).toContain("ERROR");
  });
});

// ─── HealthMonitor tests ─────────────────────────────────────

describe("HealthMonitor", () => {
  it("should return healthy when no modules", () => {
    const registry = {
      listModules: () => [],
    } as any;
    const bridge = {} as any;
    const state = new StateService();
    const audit = new AuditLogger();

    const monitor = new HealthMonitor(registry, bridge, state, audit, 60000);
    const health = monitor.getSystemHealth();

    expect(health.overall).toBe("healthy");
    expect(health.modules).toHaveLength(0);
    expect(health.uptime_ms).toBeGreaterThanOrEqual(0);
  });

  it("should track module health after check", async () => {
    const mockProxy = {
      health: vi.fn().mockResolvedValue({ status: "ok" }),
    };

    const registry = {
      listModules: () => [
        { manifest: { module_id: "mock" }, enabled: true, capabilities: [] },
      ],
    } as any;

    // Mock the ModuleProxy constructor
    const bridge = {
      request: vi.fn().mockResolvedValue({ status: "ok" }),
    } as any;

    const state = new StateService();
    const audit = new AuditLogger();

    const monitor = new HealthMonitor(registry, bridge, state, audit, 60000);

    // checkAll will try to create ModuleProxy and call health
    // Since bridge.request might fail, the module will be marked offline
    await monitor.checkAll();

    const health = monitor.getSystemHealth();
    expect(health.modules).toHaveLength(1);
  });

  it("should mark disabled modules as offline", async () => {
    const registry = {
      listModules: () => [
        { manifest: { module_id: "disabled_mod" }, enabled: false, capabilities: [] },
      ],
    } as any;

    const bridge = {} as any;
    const state = new StateService();
    const audit = new AuditLogger();

    const monitor = new HealthMonitor(registry, bridge, state, audit, 60000);
    await monitor.checkAll();

    const moduleHealth = monitor.getModuleHealth("disabled_mod");
    expect(moduleHealth?.status).toBe("offline");
    expect(moduleHealth?.details?.reason).toBe("disabled");
  });

  it("should start and stop timer", () => {
    const registry = { listModules: () => [] } as any;
    const bridge = {} as any;
    const state = new StateService();
    const audit = new AuditLogger();

    const monitor = new HealthMonitor(registry, bridge, state, audit, 60000);
    monitor.start();
    monitor.start(); // Idempotent
    monitor.stop();
    monitor.stop(); // Idempotent
  });
});
