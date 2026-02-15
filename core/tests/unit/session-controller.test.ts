/**
 * SessionController (FSM) unit tests.
 *
 * Tests:
 * - Valid state transitions
 * - Invalid transitions rejected
 * - STOP priority (any state → STOPPED)
 * - Recovery from STOPPED → IDLE
 */

import { describe, it, expect, beforeEach } from "vitest";
import { SessionController } from "../../src/orchestrator/session-controller.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { StateService } from "../../src/state/state-service.js";

const mockBridge = {
  broadcastStop: async () => {},
} as any;

describe("SessionController", () => {
  let stateService: StateService;
  let stopHandler: StopHandler;
  let controller: SessionController;

  beforeEach(() => {
    stateService = new StateService();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 100 });
    controller = new SessionController(stateService, stopHandler);
  });

  it("should start in IDLE state", () => {
    expect(controller.current).toBe("IDLE");
  });

  it("should allow valid transitions", () => {
    expect(controller.transition("THINKING")).toBe(true);
    expect(controller.current).toBe("THINKING");

    expect(controller.transition("PLANNING")).toBe(true);
    expect(controller.current).toBe("PLANNING");

    expect(controller.transition("EXECUTING")).toBe(true);
    expect(controller.current).toBe("EXECUTING");

    expect(controller.transition("RESPONDING")).toBe(true);
    expect(controller.current).toBe("RESPONDING");

    expect(controller.transition("IDLE")).toBe(true);
    expect(controller.current).toBe("IDLE");
  });

  it("should reject invalid transitions", () => {
    // IDLE → EXECUTING is not valid
    expect(controller.transition("EXECUTING")).toBe(false);
    expect(controller.current).toBe("IDLE");

    // IDLE → RESPONDING is not valid
    expect(controller.transition("RESPONDING")).toBe(false);
    expect(controller.current).toBe("IDLE");
  });

  it("should allow STOPPED from any state", () => {
    controller.transition("THINKING");
    expect(controller.transition("STOPPED")).toBe(true);
    expect(controller.current).toBe("STOPPED");
  });

  it("should only allow IDLE from STOPPED", () => {
    controller.transition("STOPPED");
    expect(controller.transition("THINKING")).toBe(false);
    expect(controller.transition("IDLE")).toBe(true);
    expect(controller.current).toBe("IDLE");
  });

  it("should force STOPPED on emergency stop", async () => {
    controller.transition("THINKING");
    await stopHandler.triggerStop("system");
    expect(controller.current).toBe("STOPPED");
  });

  it("should recover from STOPPED after cooldown", async () => {
    controller.transition("THINKING");
    await stopHandler.triggerStop("system");
    expect(controller.current).toBe("STOPPED");

    await controller.recoverFromStop();
    expect(controller.current).toBe("IDLE");
  });

  it("should emit transition events", async () => {
    const transitions: Array<{ from: string; to: string }> = [];
    controller.onTransition((from, to) => {
      transitions.push({ from, to });
    });

    controller.transition("THINKING");
    controller.transition("RESPONDING");
    controller.transition("IDLE");

    expect(transitions).toEqual([
      { from: "IDLE", to: "THINKING" },
      { from: "THINKING", to: "RESPONDING" },
      { from: "RESPONDING", to: "IDLE" },
    ]);
  });
});
