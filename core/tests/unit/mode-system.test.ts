/**
 * Mode System tests.
 *
 * Tests:
 * - Mode switching and speed limits
 * - Mute mode denies deny_when_muted capabilities
 * - Kid mode enforces speed limit (30)
 * - Safety mode enforces speed limit (50)
 * - Device memory constraints
 */

import { describe, it, expect, beforeEach } from "vitest";
import { PolicyEngine } from "../../src/safety/policy-engine.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { StateService } from "../../src/state/state-service.js";
import { MemoryService } from "../../src/memory/memory-service.js";
import type { CapabilitySpec } from "../../src/capability/types.js";
import type { Mode } from "../../src/state/types.js";

const mockBridge = {
  broadcastStop: async () => {},
} as any;

function makeSpec(overrides: Partial<CapabilitySpec> = {}): CapabilitySpec {
  return {
    capability_id: "test.cap",
    name: "Test",
    type: "tool",
    version: "1.0.0",
    description: "test",
    risk_level: "NORMAL",
    inputs_schema: {},
    outputs_schema: {},
    constraints: { timeout_ms: 5000 },
    required_state_predicates: [],
    permissions: {
      roles_allowed: ["user", "admin"],
      confirm_required: false,
    },
    idempotency: { mode: "NONE", key_fields: [], ttl_ms: 0 },
    observability: {
      audit_level: "STANDARD",
      log_inputs: true,
      log_outputs: true,
      redaction: [],
    },
    ...overrides,
  };
}

describe("Mode System", () => {
  let stateService: StateService;
  let stopHandler: StopHandler;
  let memoryService: MemoryService;
  let engine: PolicyEngine;

  beforeEach(() => {
    stateService = new StateService();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 2000 });
    memoryService = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    engine = new PolicyEngine(stopHandler, stateService, memoryService);
  });

  describe("Mode switching", () => {
    it("should default to normal mode", () => {
      expect(stateService.getMode()).toBe("normal");
    });

    it("should switch modes", () => {
      stateService.setMode("kid");
      expect(stateService.getMode()).toBe("kid");
    });

    it("should update max speed on mode change", () => {
      stateService.setMode("kid");
      expect(stateService.getMaxSpeed()).toBe(30);

      stateService.setMode("safety");
      expect(stateService.getMaxSpeed()).toBe(50);

      stateService.setMode("normal");
      expect(stateService.getMaxSpeed()).toBe(100);
    });

    it("should include mode in snapshot", () => {
      stateService.setMode("debug");
      const snapshot = stateService.getSnapshot();
      expect(snapshot.mode).toBe("debug");
    });

    it("should include apiStatus in snapshot", () => {
      const snapshot = stateService.getSnapshot();
      expect(snapshot.apiStatus).toBe("online");
    });
  });

  describe("Mute mode", () => {
    it("should deny capabilities with deny_when_muted in mute mode", async () => {
      stateService.setMode("mute");
      const spec = makeSpec({
        capability_id: "tool.voice.synthesize",
        permissions: {
          roles_allowed: ["user", "admin"],
          confirm_required: false,
          deny_when_muted: true,
        },
      });
      const result = await engine.evaluate(spec, {});
      expect(result.allowed).toBe(false);
      if (result.allowed === false) {
        expect(result.reason).toContain("mute mode");
      }
    });

    it("should allow capabilities without deny_when_muted in mute mode", async () => {
      stateService.setMode("mute");
      const spec = makeSpec({
        capability_id: "tool.voice.recognize",
        risk_level: "READ_ONLY",
        permissions: {
          roles_allowed: ["user", "admin"],
          confirm_required: false,
        },
      });
      const result = await engine.evaluate(spec, {});
      expect(result.allowed).toBe(true);
    });

    it("should allow deny_when_muted capabilities in normal mode", async () => {
      stateService.setMode("normal");
      const spec = makeSpec({
        capability_id: "tool.voice.synthesize",
        permissions: {
          roles_allowed: ["user", "admin"],
          confirm_required: false,
          deny_when_muted: true,
        },
      });
      const result = await engine.evaluate(spec, {});
      expect(result.allowed).toBe(true);
    });
  });

  describe("Kid mode speed limit", () => {
    it("should deny motion with speed > 30 in kid mode", async () => {
      stateService.setMode("kid");
      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, { speed: 50 });
      expect(result.allowed).toBe(false);
      if (result.allowed === false) {
        expect(result.reason).toContain("Speed 50");
        expect(result.reason).toContain("max 30");
      }
    });

    it("should allow motion with speed <= 30 in kid mode", async () => {
      stateService.setMode("kid");
      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, { speed: 25 });
      expect(result.allowed).toBe(true);
    });
  });

  describe("Safety mode speed limit", () => {
    it("should deny motion with speed > 50 in safety mode", async () => {
      stateService.setMode("safety");
      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, { speed: 70 });
      expect(result.allowed).toBe(false);
      if (result.allowed === false) {
        expect(result.reason).toContain("max 50");
      }
    });

    it("should allow motion with speed <= 50 in safety mode", async () => {
      stateService.setMode("safety");
      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, { speed: 50 });
      expect(result.allowed).toBe(true);
    });
  });

  describe("Normal mode", () => {
    it("should allow motion with speed <= 100 in normal mode", async () => {
      stateService.setMode("normal");
      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, { speed: 100 });
      expect(result.allowed).toBe(true);
    });
  });

  describe("Device memory constraints", () => {
    it("should deny capability when device memory has denied constraint", async () => {
      memoryService.create({
        type: "device",
        content: { capability_id: "tool.motion.forward", denied: true },
        summary: "Motor A fault: forward motion disabled",
        source: "system_detected",
        confidence: 1.0,
        privacy_level: "normal",
      });

      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, {});
      expect(result.allowed).toBe(false);
      if (result.allowed === false) {
        expect(result.reason).toContain("Device constraint");
      }
    });

    it("should allow capability without matching device constraint", async () => {
      memoryService.create({
        type: "device",
        content: { capability_id: "tool.motion.backward", denied: true },
        summary: "Motor fault: backward disabled",
        source: "system_detected",
      });

      const spec = makeSpec({ capability_id: "tool.motion.forward" });
      const result = await engine.evaluate(spec, {});
      expect(result.allowed).toBe(true);
    });
  });
});
