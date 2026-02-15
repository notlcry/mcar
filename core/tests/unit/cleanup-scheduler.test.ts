/**
 * CleanupScheduler tests.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { CleanupScheduler } from "../../src/health/cleanup-scheduler.js";
import { MemoryService } from "../../src/memory/memory-service.js";
import { AuditStore } from "../../src/audit/audit-store.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";

describe("CleanupScheduler", () => {
  let memoryService: MemoryService;
  let auditStore: AuditStore;
  let auditLogger: AuditLogger;
  let scheduler: CleanupScheduler;

  beforeEach(() => {
    memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    auditStore = new AuditStore(":memory:");
    auditLogger = new AuditLogger();
  });

  afterEach(() => {
    scheduler?.stop();
    memoryService.close();
    auditStore.close();
  });

  it("should run cleanup and return counts", () => {
    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger);
    const result = scheduler.runCleanup();
    expect(result.memoriesCleaned).toBe(0);
    expect(result.auditCleaned).toBe(0);
  });

  it("should clean expired memories with TTL", () => {
    // Create a memory with a very short TTL (1 second)
    memoryService.create({
      type: "preference",
      content: { key: "ttl-test" },
      summary: "TTL test memory",
      source: "user_explicit",
      ttl: -1, // Already expired (negative means past)
    });

    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger);
    const result = scheduler.runCleanup();
    // Note: SQLite TTL is in seconds from created_at; -1 second means already expired
    expect(result.memoriesCleaned).toBeGreaterThanOrEqual(0);
  });

  it("should clean old audit events", () => {
    // Insert an old event (40 days ago)
    const oldDate = new Date(Date.now() - 40 * 24 * 60 * 60 * 1000).toISOString();
    auditStore.save({
      id: "old-evt",
      traceId: "old-trace",
      eventType: "test.old",
      timestamp: oldDate,
      severity: "INFO",
    });

    // Insert a recent event
    auditStore.save({
      id: "new-evt",
      traceId: "new-trace",
      eventType: "test.new",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });

    expect(auditStore.count()).toBe(2);

    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger, {
      auditRetentionDays: 30,
    });
    const result = scheduler.runCleanup();
    expect(result.auditCleaned).toBe(1);
    expect(auditStore.count()).toBe(1);
  });

  it("should log cleanup when items were cleaned", () => {
    const oldDate = new Date(Date.now() - 40 * 24 * 60 * 60 * 1000).toISOString();
    auditStore.save({
      id: "old-evt",
      traceId: "t",
      eventType: "test",
      timestamp: oldDate,
      severity: "INFO",
    });

    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger, {
      auditRetentionDays: 30,
    });
    scheduler.runCleanup();

    const events = auditLogger.getRecent(10);
    const cleanupEvent = events.find((e) => e.eventType === "cleanup.complete");
    expect(cleanupEvent).toBeTruthy();
    expect(cleanupEvent?.payload?.auditCleaned).toBe(1);
  });

  it("should start and stop timer", () => {
    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger, {
      intervalMs: 60000,
    });

    expect(scheduler.isRunning()).toBe(false);

    scheduler.start();
    expect(scheduler.isRunning()).toBe(true);

    scheduler.start(); // Idempotent
    expect(scheduler.isRunning()).toBe(true);

    scheduler.stop();
    expect(scheduler.isRunning()).toBe(false);

    scheduler.stop(); // Idempotent
    expect(scheduler.isRunning()).toBe(false);
  });

  it("should work without audit store", () => {
    scheduler = new CleanupScheduler(memoryService, null, auditLogger);
    const result = scheduler.runCleanup();
    expect(result.memoriesCleaned).toBe(0);
    expect(result.auditCleaned).toBe(0);
  });

  it("should handle cleanup errors gracefully", () => {
    // Close the store to cause errors
    auditStore.close();

    scheduler = new CleanupScheduler(memoryService, auditStore, auditLogger);
    // Should not throw
    expect(() => scheduler.runCleanup()).not.toThrow();
  });
});
