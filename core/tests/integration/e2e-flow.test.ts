/**
 * E2E flow integration tests.
 *
 * Uses real services (SessionController, ActionDispatcher, PolicyEngine,
 * StateService, MemoryService, AuditLogger, StopHandler) with mock
 * AgentRuntime and ModuleBridge to verify end-to-end behavior.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { StateService } from "../../src/state/state-service.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { SessionController } from "../../src/orchestrator/session-controller.js";
import { ActionDispatcher } from "../../src/orchestrator/action-dispatcher.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";
import { MemoryService } from "../../src/memory/memory-service.js";
import { PolicyEngine } from "../../src/safety/policy-engine.js";
import { PerformanceTracker } from "../../src/observability/performance-tracker.js";

// ─── Mock factories ─────────────────────────────────────────

function createMockBridge() {
  return {
    broadcastStop: vi.fn().mockResolvedValue(undefined),
    onEvent: vi.fn().mockReturnValue(() => {}),
    onRegister: vi.fn().mockReturnValue(() => {}),
    getRegisteredModules: vi.fn().mockReturnValue(["mock"]),
  } as any;
}

/**
 * Create a mock AgentRuntime that simulates LLM text response.
 * Calls the subscriber with text_delta events to produce the response.
 */
function createMockAgent(responseText: string = "Hello! How can I help?") {
  let subscriberFn: ((event: any) => void) | null = null;

  return {
    prompt: vi.fn().mockImplementation(async () => {
      // Simulate streaming response
      if (subscriberFn) {
        subscriberFn({
          type: "message_update",
          assistantMessageEvent: {
            type: "text_delta",
            delta: responseText,
          },
        });
      }
    }),
    subscribe: vi.fn().mockImplementation((fn: (event: any) => void) => {
      subscriberFn = fn;
      return () => {
        subscriberFn = null;
      };
    }),
    abort: vi.fn(),
    clearMessages: vi.fn(),
    setResponseText(text: string) {
      responseText = text;
    },
  } as any;
}

// ─── Test suite ─────────────────────────────────────────────

describe("E2E Flow", () => {
  let stateService: StateService;
  let stopHandler: StopHandler;
  let session: SessionController;
  let dispatcher: ActionDispatcher;
  let auditLogger: AuditLogger;
  let memoryService: MemoryService;
  let policyEngine: PolicyEngine;
  let perfTracker: PerformanceTracker;
  let mockBridge: ReturnType<typeof createMockBridge>;
  let mockAgent: ReturnType<typeof createMockAgent>;

  beforeEach(() => {
    mockBridge = createMockBridge();
    mockAgent = createMockAgent();

    stateService = new StateService();
    auditLogger = new AuditLogger();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 500 });
    memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    policyEngine = new PolicyEngine(stopHandler, stateService, memoryService);
    perfTracker = new PerformanceTracker();
    session = new SessionController(stateService, stopHandler);
    dispatcher = new ActionDispatcher(
      session,
      mockAgent,
      auditLogger,
      stopHandler,
      perfTracker,
      memoryService
    );
  });

  // ─── Basic text flow ────────────────────────────────────

  it("should complete text input → response cycle", async () => {
    expect(session.current).toBe("IDLE");

    const response = await dispatcher.dispatch("你好");

    expect(response).toBe("Hello! How can I help?");
    expect(session.current).toBe("IDLE");
    expect(mockAgent.prompt).toHaveBeenCalledWith("你好");
  });

  it("should record FSM transitions through THINKING → RESPONDING → IDLE", async () => {
    const transitions: string[] = [];
    session.onTransition((_from, to) => {
      transitions.push(to);
    });

    await dispatcher.dispatch("hello");

    expect(transitions).toEqual(["THINKING", "RESPONDING", "IDLE"]);
  });

  it("should record dispatch.cycle latency in PerformanceTracker", async () => {
    await dispatcher.dispatch("test");

    const metrics = perfTracker.getMetrics("dispatch.cycle");
    expect(metrics).not.toBeNull();
    expect(metrics!.count).toBeGreaterThanOrEqual(1);
  });

  // ─── Emergency stop ─────────────────────────────────────

  it("should trigger emergency stop on stop words", async () => {
    const response = await dispatcher.dispatch("停");

    expect(response).toContain("Emergency stop");
    expect(mockBridge.broadcastStop).toHaveBeenCalledWith("voice");
    expect(stopHandler.isLocked()).toBe(true);
  });

  it("should reject non-readonly operations during safety lock", async () => {
    // Trigger stop to activate safety lock
    await dispatcher.dispatch("停止");
    expect(stopHandler.isLocked()).toBe(true);

    // Evaluate a NORMAL risk capability during lock
    const decision = await policyEngine.evaluate(
      {
        capability_id: "tool.motion.forward",
        risk_level: "NORMAL",
        required_state_predicates: [],
        permissions: { roles_allowed: ["user"], confirm_required: false },
      } as any,
      {}
    );

    expect(decision.allowed).toBe(false);
    expect(decision.code).toBe("E_STATE_ESTOP");
  });

  it("should allow READ_ONLY operations during safety lock", async () => {
    await dispatcher.dispatch("emergency");
    expect(stopHandler.isLocked()).toBe(true);

    const decision = await policyEngine.evaluate(
      {
        capability_id: "tool.sensor.ultrasonic",
        risk_level: "READ_ONLY",
        required_state_predicates: [],
        permissions: { roles_allowed: ["user"], confirm_required: false },
      } as any,
      {}
    );

    expect(decision.allowed).toBe(true);
  });

  it("should recover from stop after cooldown", async () => {
    await dispatcher.dispatch("stop");

    // Force transition to STOPPED
    session.transition("STOPPED");
    expect(session.current).toBe("STOPPED");

    // Wait for cooldown (500ms configured)
    await session.recoverFromStop();
    expect(session.current).toBe("IDLE");
  });

  // ─── Confirmation flow ──────────────────────────────────

  it("should handle dangerous action confirmation flow", async () => {
    const confirmPromise = dispatcher.requestConfirmation(
      "Delete all data?",
      "Say yes to proceed"
    );

    expect(dispatcher.getPendingConfirmation()).not.toBeNull();

    const response = await dispatcher.dispatch("确认");
    expect(response).toBe("Confirmed. Executing...");

    const confirmed = await confirmPromise;
    expect(confirmed).toBe(true);
  });

  it("should handle dangerous action rejection", async () => {
    const confirmPromise = dispatcher.requestConfirmation(
      "Delete all data?",
      "Say yes to proceed"
    );

    const response = await dispatcher.dispatch("取消");
    expect(response).toBe("Cancelled.");

    const confirmed = await confirmPromise;
    expect(confirmed).toBe(false);
  });

  // ─── Memory proposal flow ───────────────────────────────

  it("should save memory after proposal confirmation", async () => {
    const proposal = {
      type: "preference",
      summary: "User prefers slow speed",
      content: JSON.stringify({ speed: "slow" }),
    };

    dispatcher.requestMemoryConfirmation(proposal);
    const response = await dispatcher.dispatch("是");

    expect(response).toBe("Confirmed. Memory saved.");

    // Verify memory was written
    const memories = memoryService.listSummaries();
    expect(memories.some((m) => m.summary === "User prefers slow speed")).toBe(true);
  });

  it("should not save memory after proposal rejection", async () => {
    const proposal = {
      type: "fact",
      summary: "User lives in Tokyo",
    };

    dispatcher.requestMemoryConfirmation(proposal);
    const response = await dispatcher.dispatch("cancel");

    expect(response).toBe("Cancelled.");

    const memories = memoryService.listSummaries();
    expect(memories.some((m) => m.summary === "User lives in Tokyo")).toBe(false);
  });

  // ─── Mode and policy integration ───────────────────────

  it("should enforce speed limits based on mode", async () => {
    stateService.setMode("kid");

    const decision = await policyEngine.evaluate(
      {
        capability_id: "tool.motion.forward",
        risk_level: "NORMAL",
        required_state_predicates: [],
        permissions: { roles_allowed: ["user"], confirm_required: false },
      } as any,
      { speed: 50 }
    );

    // kid mode max speed is 30, requesting 50 should be denied
    expect(decision.allowed).toBe(false);
    expect(decision.reason).toContain("Speed 50 exceeds max 30");
  });

  it("should allow within-limit speed in kid mode", async () => {
    stateService.setMode("kid");

    const decision = await policyEngine.evaluate(
      {
        capability_id: "tool.motion.forward",
        risk_level: "NORMAL",
        required_state_predicates: [],
        permissions: { roles_allowed: ["user"], confirm_required: false },
      } as any,
      { speed: 25 }
    );

    expect(decision.allowed).toBe(true);
  });

  // ─── State transitions edge cases ──────────────────────

  it("should reject dispatch when not in IDLE state", async () => {
    // Force into RESPONDING state (RESPONDING → THINKING is invalid)
    session.transition("THINKING");
    session.transition("RESPONDING");

    const response = await dispatcher.dispatch("hello");

    expect(response).toContain("Cannot process");
    expect(response).toContain("RESPONDING");
  });

  it("should handle agent errors gracefully and return error message", async () => {
    mockAgent.prompt.mockRejectedValueOnce(new Error("API timeout"));

    const response = await dispatcher.dispatch("test");

    expect(response).toContain("Error:");
    expect(response).toContain("API timeout");
  });
});
