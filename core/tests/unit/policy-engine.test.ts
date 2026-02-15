/**
 * PolicyEngine unit tests.
 *
 * Tests:
 * - READ_ONLY capabilities bypass most checks
 * - NORMAL capabilities blocked during e-stop
 * - DANGEROUS capabilities require confirmation
 * - State predicates (DENY / CONFIRM)
 * - Role-based access control
 */

import { describe, it, expect, beforeEach } from "vitest";
import { PolicyEngine } from "../../src/safety/policy-engine.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { StateService } from "../../src/state/state-service.js";
import type { CapabilitySpec } from "../../src/capability/types.js";

// Minimal mock bridge with just broadcastStop
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

describe("PolicyEngine", () => {
  let stateService: StateService;
  let stopHandler: StopHandler;
  let engine: PolicyEngine;

  beforeEach(() => {
    stateService = new StateService();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 2000 });
    engine = new PolicyEngine(stopHandler, stateService);
  });

  it("should allow READ_ONLY capabilities", async () => {
    const spec = makeSpec({ risk_level: "READ_ONLY" });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(true);
  });

  it("should allow NORMAL capabilities when no restrictions", async () => {
    const spec = makeSpec({ risk_level: "NORMAL" });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(true);
  });

  it("should block NORMAL during e-stop", async () => {
    await stopHandler.triggerStop("system");
    const spec = makeSpec({ risk_level: "NORMAL" });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(false);
    if (result.allowed === false) {
      expect(result.code).toBe("E_STATE_ESTOP");
      expect(result.retryable).toBe(true);
    }
  });

  it("should still allow READ_ONLY during e-stop", async () => {
    await stopHandler.triggerStop("system");
    const spec = makeSpec({ risk_level: "READ_ONLY" });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(true);
  });

  it("should require confirmation for DANGEROUS capabilities", async () => {
    const spec = makeSpec({
      risk_level: "DANGEROUS",
      permissions: {
        roles_allowed: ["user", "admin"],
        confirm_required: true,
        confirm_phrase_hint: "Are you sure?",
      },
    });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe("confirm");
  });

  it("should allow DANGEROUS when confirmed", async () => {
    const spec = makeSpec({
      risk_level: "DANGEROUS",
      permissions: {
        roles_allowed: ["user", "admin"],
        confirm_required: true,
      },
    });
    const result = await engine.evaluate(spec, {}, { confirmed: true });
    expect(result.allowed).toBe(true);
  });

  it("should deny if role is not allowed", async () => {
    const spec = makeSpec({
      permissions: {
        roles_allowed: ["admin"],
        confirm_required: false,
      },
    });
    const result = await engine.evaluate(spec, {}, { role: "user" });
    expect(result.allowed).toBe(false);
    if (result.allowed === false) {
      expect(result.code).toBe("E_POLICY_ROLE_DENIED");
    }
  });

  it("should deny when state predicate fails with DENY", async () => {
    stateService.set("obstacle", true);
    const spec = makeSpec({
      required_state_predicates: [
        { key: "obstacle", op: "==", value: false, on_fail: "DENY" },
      ],
    });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(false);
  });

  it("should request confirm when state predicate fails with CONFIRM", async () => {
    stateService.set("obstacle", true);
    const spec = makeSpec({
      required_state_predicates: [
        { key: "obstacle", op: "==", value: false, on_fail: "CONFIRM" },
      ],
    });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe("confirm");
  });

  it("should pass when state predicate is satisfied", async () => {
    stateService.set("obstacle", false);
    const spec = makeSpec({
      required_state_predicates: [
        { key: "obstacle", op: "==", value: false, on_fail: "DENY" },
      ],
    });
    const result = await engine.evaluate(spec, {});
    expect(result.allowed).toBe(true);
  });
});
