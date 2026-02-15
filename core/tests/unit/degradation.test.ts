/**
 * DegradationHandler unit tests.
 *
 * Tests:
 * - Tracks consecutive failures
 * - Enters degraded mode after threshold
 * - Recovers on success
 * - Parses basic motion commands
 * - Provides offline responses
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { DegradationHandler } from "../../src/agent/degradation-handler.js";
import { StateService } from "../../src/state/state-service.js";
import type { AuditLogger } from "../../src/audit/audit-logger.js";

const mockAudit: AuditLogger = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  getEntries: vi.fn(() => []),
} as any;

describe("DegradationHandler", () => {
  let stateService: StateService;
  let handler: DegradationHandler;

  beforeEach(() => {
    vi.clearAllMocks();
    stateService = new StateService();
    handler = new DegradationHandler(stateService, mockAudit, 3, 30_000);
  });

  describe("Failure tracking", () => {
    it("should not be degraded initially", () => {
      expect(handler.isDegraded()).toBe(false);
    });

    it("should not be degraded after 1 failure", () => {
      handler.recordFailure("timeout");
      expect(handler.isDegraded()).toBe(false);
    });

    it("should not be degraded after 2 failures", () => {
      handler.recordFailure("timeout");
      handler.recordFailure("network error");
      expect(handler.isDegraded()).toBe(false);
    });

    it("should enter degraded mode after 3 consecutive failures", () => {
      handler.recordFailure("timeout");
      handler.recordFailure("timeout");
      handler.recordFailure("timeout");
      expect(handler.isDegraded()).toBe(true);
      expect(stateService.getApiStatus()).toBe("degraded");
    });

    it("should reset failure count on success", () => {
      handler.recordFailure("timeout");
      handler.recordFailure("timeout");
      handler.recordSuccess();
      handler.recordFailure("timeout");
      // Only 1 failure after reset, not enough for degradation
      expect(handler.isDegraded()).toBe(false);
    });
  });

  describe("Recovery", () => {
    it("should recover on success after degradation", () => {
      handler.recordFailure("e1");
      handler.recordFailure("e2");
      handler.recordFailure("e3");
      expect(handler.isDegraded()).toBe(true);

      handler.recordSuccess();
      expect(handler.isDegraded()).toBe(false);
      expect(stateService.getApiStatus()).toBe("online");
    });
  });

  describe("Basic command parsing", () => {
    it("should parse Chinese motion commands", () => {
      expect(handler.parseBasicCommand("前进")).toEqual({
        capability: "tool.motion.forward",
        params: { speed: 30, duration_ms: 1000 },
      });
      expect(handler.parseBasicCommand("后退")).toEqual({
        capability: "tool.motion.backward",
        params: { speed: 30, duration_ms: 1000 },
      });
      expect(handler.parseBasicCommand("左转")).toEqual({
        capability: "tool.motion.turn_left",
        params: { speed: 30, duration_ms: 500 },
      });
      expect(handler.parseBasicCommand("右转")).toEqual({
        capability: "tool.motion.turn_right",
        params: { speed: 30, duration_ms: 500 },
      });
      expect(handler.parseBasicCommand("停止")).toEqual({
        capability: "tool.motion.stop",
        params: {},
      });
    });

    it("should parse English motion commands", () => {
      expect(handler.parseBasicCommand("forward")).toEqual({
        capability: "tool.motion.forward",
        params: { speed: 30, duration_ms: 1000 },
      });
      expect(handler.parseBasicCommand("stop")).toEqual({
        capability: "tool.motion.stop",
        params: {},
      });
    });

    it("should return null for unrecognized commands", () => {
      expect(handler.parseBasicCommand("what is the weather")).toBeNull();
      expect(handler.parseBasicCommand("hello")).toBeNull();
    });

    it("should handle whitespace and case", () => {
      expect(handler.parseBasicCommand("  Forward  ")).toEqual({
        capability: "tool.motion.forward",
        params: { speed: 30, duration_ms: 1000 },
      });
    });
  });

  describe("Offline responses", () => {
    it("should return a Chinese offline response", () => {
      const response = handler.getOfflineResponse();
      expect(typeof response).toBe("string");
      expect(response.length).toBeGreaterThan(0);
    });
  });

  describe("State tracking", () => {
    it("should update apiStatus to degraded", () => {
      handler.recordFailure("e1");
      handler.recordFailure("e2");
      handler.recordFailure("e3");
      expect(stateService.getSnapshot().apiStatus).toBe("degraded");
    });

    it("should update apiStatus to online on recovery", () => {
      handler.recordFailure("e1");
      handler.recordFailure("e2");
      handler.recordFailure("e3");
      handler.recordSuccess();
      expect(stateService.getSnapshot().apiStatus).toBe("online");
    });
  });
});
