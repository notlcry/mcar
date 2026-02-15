/**
 * ActionDispatcher unit tests.
 *
 * Tests:
 * - Memory proposal confirmation → writes to MemoryService
 * - Memory proposal rejection → does not write
 * - Memory proposal timeout → does not write
 * - dispatch.cycle recorded in PerformanceTracker
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { ActionDispatcher } from "../../src/orchestrator/action-dispatcher.js";
import type { SessionController } from "../../src/orchestrator/session-controller.js";
import type { AgentRuntime } from "../../src/agent/agent-runtime.js";
import type { AuditLogger } from "../../src/audit/audit-logger.js";
import type { StopHandler } from "../../src/safety/stop-handler.js";
import type { PerformanceTracker } from "../../src/observability/performance-tracker.js";
import type { MemoryService } from "../../src/memory/memory-service.js";

function createMockSession(): SessionController {
  return {
    current: "IDLE",
    transition: vi.fn().mockReturnValue(true),
  } as any;
}

function createMockAgent(): AgentRuntime {
  return {
    prompt: vi.fn().mockResolvedValue(undefined),
    subscribe: vi.fn().mockReturnValue(() => {}),
  } as any;
}

function createMockAudit(): AuditLogger {
  return {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  } as any;
}

function createMockStopHandler(): StopHandler {
  return {
    triggerStop: vi.fn().mockResolvedValue(undefined),
  } as any;
}

function createMockPerformanceTracker(): PerformanceTracker {
  const records: Array<{ operation: string; duration: number }> = [];
  return {
    startTimer: vi.fn().mockImplementation((op: string) => {
      const start = Date.now();
      return () => {
        const d = Date.now() - start;
        records.push({ operation: op, duration: d });
        return d;
      };
    }),
    record: vi.fn(),
    getMetrics: vi.fn().mockImplementation((op: string) => {
      const matching = records.filter((r) => r.operation === op);
      return matching.length > 0 ? { count: matching.length } : null;
    }),
    getAllMetrics: vi.fn().mockReturnValue([]),
    _records: records,
  } as any;
}

function createMockMemoryService(): MemoryService {
  const memories: any[] = [];
  return {
    create: vi.fn().mockImplementation((input: any) => {
      const entry = { id: `mem-${memories.length}`, ...input };
      memories.push(entry);
      return entry;
    }),
    getById: vi.fn(),
    _memories: memories,
  } as any;
}

describe("ActionDispatcher", () => {
  let session: ReturnType<typeof createMockSession>;
  let agent: ReturnType<typeof createMockAgent>;
  let audit: ReturnType<typeof createMockAudit>;
  let stopHandler: ReturnType<typeof createMockStopHandler>;
  let perfTracker: ReturnType<typeof createMockPerformanceTracker>;
  let memoryService: ReturnType<typeof createMockMemoryService>;
  let dispatcher: ActionDispatcher;

  beforeEach(() => {
    session = createMockSession();
    agent = createMockAgent();
    audit = createMockAudit();
    stopHandler = createMockStopHandler();
    perfTracker = createMockPerformanceTracker();
    memoryService = createMockMemoryService();
    dispatcher = new ActionDispatcher(
      session,
      agent,
      audit,
      stopHandler,
      perfTracker,
      memoryService
    );
  });

  // ─── Memory proposal confirmation ─────────────────────────

  it("should write memory to MemoryService when proposal is confirmed", async () => {
    const proposal = {
      type: "preference",
      summary: "User likes slow speed",
      content: JSON.stringify({ speed: "slow" }),
    };

    // Start confirmation flow (don't await — we'll respond synchronously)
    const confirmPromise = dispatcher.requestMemoryConfirmation(proposal);

    // User confirms
    const response = await dispatcher.dispatch("yes");

    expect(response).toBe("Confirmed. Memory saved.");
    expect(memoryService.create).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "preference",
        summary: "User likes slow speed",
        source: "agent_proposed",
      })
    );
  });

  it("should not write memory when proposal is rejected", async () => {
    const proposal = {
      type: "fact",
      summary: "User lives in Beijing",
    };

    dispatcher.requestMemoryConfirmation(proposal);

    const response = await dispatcher.dispatch("no");

    expect(response).toBe("Cancelled.");
    expect(memoryService.create).not.toHaveBeenCalled();
  });

  it("should not write memory on unrecognized response", async () => {
    const proposal = {
      type: "rule",
      summary: "Never go above 50",
    };

    dispatcher.requestMemoryConfirmation(proposal);

    const response = await dispatcher.dispatch("maybe");

    expect(response).toBe("Confirmation cancelled (unrecognized response).");
    expect(memoryService.create).not.toHaveBeenCalled();
  });

  // ─── PerformanceTracker integration ───────────────────────

  it("should record dispatch.cycle in PerformanceTracker", async () => {
    await dispatcher.dispatch("hello");

    expect(perfTracker.startTimer).toHaveBeenCalledWith("dispatch.cycle");
  });
});
