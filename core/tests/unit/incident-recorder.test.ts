/**
 * IncidentRecorder unit tests.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { IncidentRecorder } from "../../src/observability/incident-recorder.js";
import { MemoryService } from "../../src/memory/memory-service.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";

describe("IncidentRecorder", () => {
  let memoryService: MemoryService;
  let auditLogger: AuditLogger;
  let recorder: IncidentRecorder;

  beforeEach(() => {
    memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    auditLogger = new AuditLogger();
    recorder = new IncidentRecorder(memoryService, auditLogger);
  });

  afterEach(() => {
    memoryService.close();
  });

  it("should create an incident memory", () => {
    const id = recorder.record({
      category: "module_crash",
      error_code: "EXIT_1",
      message: "Module mock crashed",
      module_id: "mock",
    });

    expect(id).not.toBeNull();
    const entry = memoryService.getById(id!);
    expect(entry).not.toBeNull();
    expect(entry!.type).toBe("incident");
    expect(entry!.summary).toContain("module_crash");
    expect(entry!.summary).toContain("EXIT_1");
  });

  it("should deduplicate within TTL", () => {
    const id1 = recorder.record({
      category: "tool_error",
      error_code: "E_TIMEOUT",
      message: "Timeout on tool.mock.echo",
      capability_id: "tool.mock.echo",
    });

    const id2 = recorder.record({
      category: "tool_error",
      error_code: "E_TIMEOUT",
      message: "Timeout on tool.mock.echo again",
      capability_id: "tool.mock.echo",
    });

    expect(id1).not.toBeNull();
    expect(id2).toBeNull();
  });

  it("should allow duplicate after TTL expires", () => {
    vi.useFakeTimers();
    try {
      const id1 = recorder.record({
        category: "tool_error",
        error_code: "E_TIMEOUT",
        message: "first",
        capability_id: "tool.mock.echo",
      });
      expect(id1).not.toBeNull();

      // Advance past dedup TTL (60s)
      vi.advanceTimersByTime(61_000);

      const id2 = recorder.record({
        category: "tool_error",
        error_code: "E_TIMEOUT",
        message: "second",
        capability_id: "tool.mock.echo",
      });
      expect(id2).not.toBeNull();
      expect(id2).not.toBe(id1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("should set source to system_detected", () => {
    const id = recorder.record({
      category: "api_degradation",
      error_code: "API_CONSECUTIVE_FAILURES",
      message: "API degraded",
    });

    const entry = memoryService.getById(id!);
    expect(entry!.source).toBe("system_detected");
  });

  it("should include error_code in tags", () => {
    const id = recorder.record({
      category: "tool_error",
      error_code: "E_INTERNAL",
      message: "internal error",
      capability_id: "tool.test",
    });

    const entry = memoryService.getById(id!);
    expect(entry!.tags).toContain("incident");
    expect(entry!.tags).toContain("tool_error");
    expect(entry!.tags).toContain("E_INTERNAL");
  });

  it("should include capability_id in content", () => {
    const id = recorder.record({
      category: "tool_error",
      error_code: "E_TIMEOUT",
      message: "timeout",
      capability_id: "tool.motion.forward",
    });

    const entry = memoryService.getById(id!);
    expect(entry!.content.capability_id).toBe("tool.motion.forward");
  });

  it("should handle missing optional fields without crash", () => {
    const id = recorder.record({
      category: "api_degradation",
      error_code: "API_DOWN",
      message: "API is down",
    });

    expect(id).not.toBeNull();
    const entry = memoryService.getById(id!);
    expect(entry!.content.capability_id).toBeUndefined();
    expect(entry!.content.module_id).toBeUndefined();
  });

  it("should set TTL in seconds (7 days = 604800s)", () => {
    const id = recorder.record({
      category: "module_crash",
      error_code: "EXIT_1",
      message: "crash",
      module_id: "mock",
    });

    const entry = memoryService.getById(id!);
    expect(entry!.ttl).toBe(7 * 24 * 60 * 60); // 604800 seconds
    expect(entry!.ttl).toBeLessThan(1_000_000); // Sanity: not milliseconds
  });

  it("should write audit log on record", () => {
    recorder.record({
      category: "module_crash",
      error_code: "EXIT_SIGTERM",
      message: "Module crashed",
      module_id: "voice",
    });

    const events = auditLogger.getRecent(10);
    const incident = events.find((e) => e.eventType === "incident.recorded");
    expect(incident).toBeTruthy();
    expect(incident!.payload?.category).toBe("module_crash");
    expect(incident!.payload?.error_code).toBe("EXIT_SIGTERM");
  });
});
