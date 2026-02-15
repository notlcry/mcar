/**
 * SkillEngine unit tests.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { SkillEngine } from "../../src/skill/skill-engine.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";
import { StateService } from "../../src/state/state-service.js";
import type { SkillDefinition } from "../../src/skill/types.js";
import type { CapabilityExecutor, ExecutionResult } from "../../src/capability/executor.js";
import type { PolicyEngine } from "../../src/safety/policy-engine.js";
import type { CapabilityRegistry } from "../../src/capability/registry.js";

// ─── Mock factories ─────────────────────────────────────────

function makeSuccessResult(data: Record<string, unknown> = {}): ExecutionResult {
  return { success: true, data };
}

function makeErrorResult(message: string): ExecutionResult {
  return { success: false, error: { code: "E_INTERNAL", message } };
}

function createMocks() {
  const executor = {
    execute: vi.fn().mockResolvedValue(makeSuccessResult({ ok: true })),
  } as unknown as CapabilityExecutor;

  const policyEngine = {
    evaluate: vi.fn().mockResolvedValue({ allowed: true }),
  } as unknown as PolicyEngine;

  const registry = {
    getCapability: vi.fn().mockReturnValue({
      spec: { capability_id: "test", risk_level: "READ_ONLY" },
      moduleId: "mock",
    }),
  } as unknown as CapabilityRegistry;

  const stateService = new StateService();
  const auditLogger = new AuditLogger();

  return { executor, policyEngine, registry, stateService, auditLogger };
}

// ─── Test skill definitions ──────────────────────────────────

const SIMPLE_SKILL: SkillDefinition = {
  skill_id: "skill.test.simple",
  name: "Simple Test",
  description: "A two-step test skill",
  version: "1.0.0",
  risk_level: "READ_ONLY",
  steps: [
    { id: "step1", capability_id: "tool.sensor.ultrasonic", params: {} },
    { id: "step2", capability_id: "tool.sensor.infrared", params: {} },
  ],
};

const CONDITIONAL_SKILL: SkillDefinition = {
  skill_id: "skill.test.conditional",
  name: "Conditional Test",
  description: "Skill with step condition",
  version: "1.0.0",
  risk_level: "NORMAL",
  steps: [
    { id: "check", capability_id: "tool.sensor.infrared", params: {} },
    {
      id: "move",
      capability_id: "tool.motion.forward",
      params: { speed: 30, duration_ms: 1000 },
      condition: {
        type: "previous_result",
        path: "check.left_obstacle",
        op: "==",
        value: false,
      },
    },
  ],
};

const PARAM_SKILL: SkillDefinition = {
  skill_id: "skill.test.params",
  name: "Parameterized Test",
  description: "Skill with parameter substitution",
  version: "1.0.0",
  risk_level: "NORMAL",
  parameters: {
    speed: { type: "integer", default: 30 },
  },
  steps: [
    {
      id: "move",
      capability_id: "tool.motion.forward",
      params: { speed: "${speed}", duration_ms: 1000 },
    },
  ],
};

const REF_SKILL: SkillDefinition = {
  skill_id: "skill.test.refs",
  name: "Ref Test",
  description: "Skill with param_refs",
  version: "1.0.0",
  risk_level: "READ_ONLY",
  steps: [
    { id: "read", capability_id: "tool.sensor.ultrasonic", params: {} },
    {
      id: "report",
      capability_id: "tool.voice.synthesize",
      params: { voice: "default" },
      param_refs: { text: "read.distance_cm" },
    },
  ],
};

const ERROR_SKILL: SkillDefinition = {
  skill_id: "skill.test.error",
  name: "Error Test",
  description: "Skill with error handling",
  version: "1.0.0",
  risk_level: "READ_ONLY",
  steps: [
    {
      id: "fail_skip",
      capability_id: "tool.broken",
      params: {},
      on_error: "skip",
    },
    {
      id: "succeed",
      capability_id: "tool.sensor.ultrasonic",
      params: {},
    },
  ],
};

const RETRY_SKILL: SkillDefinition = {
  skill_id: "skill.test.retry",
  name: "Retry Test",
  description: "Skill with retry on error",
  version: "1.0.0",
  risk_level: "READ_ONLY",
  steps: [
    {
      id: "flaky",
      capability_id: "tool.flaky",
      params: {},
      on_error: "retry",
      max_retries: 2,
    },
  ],
};

// ─── Tests ───────────────────────────────────────────────────

describe("SkillEngine", () => {
  let engine: SkillEngine;
  let mocks: ReturnType<typeof createMocks>;

  beforeEach(() => {
    mocks = createMocks();
    engine = new SkillEngine(
      mocks.executor,
      mocks.policyEngine,
      mocks.registry,
      mocks.stateService,
      mocks.auditLogger
    );
  });

  describe("registration", () => {
    it("should register and list skills", () => {
      engine.registerSkill(SIMPLE_SKILL);
      engine.registerSkill(CONDITIONAL_SKILL);
      expect(engine.listSkills()).toHaveLength(2);
    });

    it("should get skill by ID", () => {
      engine.registerSkill(SIMPLE_SKILL);
      expect(engine.getSkill("skill.test.simple")).toEqual(SIMPLE_SKILL);
      expect(engine.getSkill("nonexistent")).toBeUndefined();
    });

    it("should unregister skills", () => {
      engine.registerSkill(SIMPLE_SKILL);
      expect(engine.unregisterSkill("skill.test.simple")).toBe(true);
      expect(engine.listSkills()).toHaveLength(0);
      expect(engine.unregisterSkill("nonexistent")).toBe(false);
    });
  });

  describe("execution", () => {
    it("should execute a simple multi-step skill", async () => {
      engine.registerSkill(SIMPLE_SKILL);

      const result = await engine.execute("skill.test.simple");

      expect(result.success).toBe(true);
      expect(result.steps_completed).toBe(2);
      expect(result.steps_total).toBe(2);
      expect(mocks.executor.execute).toHaveBeenCalledTimes(2);
    });

    it("should return error for unknown skill", async () => {
      const result = await engine.execute("skill.nonexistent");
      expect(result.success).toBe(false);
      expect(result.error).toContain("not found");
    });

    it("should evaluate conditions and skip steps", async () => {
      engine.registerSkill(CONDITIONAL_SKILL);

      // Sensor returns obstacle detected
      vi.mocked(mocks.executor.execute)
        .mockResolvedValueOnce(makeSuccessResult({ ok: true, left_obstacle: true }))
        .mockResolvedValueOnce(makeSuccessResult({ ok: true }));

      const result = await engine.execute("skill.test.conditional");

      expect(result.success).toBe(true);
      expect(result.steps_completed).toBe(2);
      // Move step should be skipped due to obstacle
      expect(result.results["move"]).toEqual({ skipped: true, reason: "condition_not_met" });
      // Only the sensor call should have been executed
      expect(mocks.executor.execute).toHaveBeenCalledTimes(1);
    });

    it("should execute conditional step when condition met", async () => {
      engine.registerSkill(CONDITIONAL_SKILL);

      vi.mocked(mocks.executor.execute)
        .mockResolvedValueOnce(makeSuccessResult({ ok: true, left_obstacle: false }))
        .mockResolvedValueOnce(makeSuccessResult({ ok: true }));

      const result = await engine.execute("skill.test.conditional");

      expect(result.success).toBe(true);
      expect(mocks.executor.execute).toHaveBeenCalledTimes(2);
    });

    it("should substitute skill parameters", async () => {
      engine.registerSkill(PARAM_SKILL);

      await engine.execute("skill.test.params", { speed: 50 });

      expect(mocks.executor.execute).toHaveBeenCalledWith(
        "tool.motion.forward",
        expect.objectContaining({ speed: 50, duration_ms: 1000 })
      );
    });

    it("should resolve param_refs from previous step results", async () => {
      engine.registerSkill(REF_SKILL);

      vi.mocked(mocks.executor.execute)
        .mockResolvedValueOnce(makeSuccessResult({ ok: true, distance_cm: 42.5 }))
        .mockResolvedValueOnce(makeSuccessResult({ ok: true }));

      const result = await engine.execute("skill.test.refs");

      expect(result.success).toBe(true);
      expect(mocks.executor.execute).toHaveBeenNthCalledWith(
        2,
        "tool.voice.synthesize",
        expect.objectContaining({ text: 42.5, voice: "default" })
      );
    });

    it("should skip step on error when on_error is skip", async () => {
      engine.registerSkill(ERROR_SKILL);

      vi.mocked(mocks.executor.execute)
        .mockResolvedValueOnce(makeErrorResult("broken tool"))
        .mockResolvedValueOnce(makeSuccessResult({ ok: true }));

      const result = await engine.execute("skill.test.error");

      expect(result.success).toBe(true);
      expect(result.steps_completed).toBe(2);
      expect(result.results["fail_skip"]).toEqual({ skipped: true, error: "broken tool" });
    });

    it("should abort on error when on_error is abort (default)", async () => {
      const abortSkill: SkillDefinition = {
        skill_id: "skill.test.abort",
        name: "Abort Test",
        description: "Aborts on first error",
        version: "1.0.0",
        risk_level: "READ_ONLY",
        steps: [
          { id: "fail", capability_id: "tool.broken", params: {} },
          { id: "never", capability_id: "tool.sensor.ultrasonic", params: {} },
        ],
      };

      engine.registerSkill(abortSkill);
      vi.mocked(mocks.executor.execute).mockResolvedValueOnce(makeErrorResult("broken"));

      const result = await engine.execute("skill.test.abort");

      expect(result.success).toBe(false);
      expect(result.aborted_at_step).toBe("fail");
      expect(result.steps_completed).toBe(0);
      expect(mocks.executor.execute).toHaveBeenCalledTimes(1);
    });

    it("should retry on error when on_error is retry", async () => {
      engine.registerSkill(RETRY_SKILL);

      vi.mocked(mocks.executor.execute)
        .mockResolvedValueOnce(makeErrorResult("fail 1"))
        .mockResolvedValueOnce(makeErrorResult("fail 2"))
        .mockResolvedValueOnce(makeSuccessResult({ ok: true }));

      const result = await engine.execute("skill.test.retry");

      expect(result.success).toBe(true);
      // 1 original + 2 retries = 3 calls
      expect(mocks.executor.execute).toHaveBeenCalledTimes(3);
    });

    it("should abort after max retries exceeded", async () => {
      engine.registerSkill(RETRY_SKILL);

      vi.mocked(mocks.executor.execute)
        .mockResolvedValue(makeErrorResult("always fails"));

      const result = await engine.execute("skill.test.retry");

      expect(result.success).toBe(false);
      expect(result.aborted_at_step).toBe("flaky");
      // 1 original + 2 retries = 3 calls
      expect(mocks.executor.execute).toHaveBeenCalledTimes(3);
    });

    it("should respect policy denials", async () => {
      engine.registerSkill(SIMPLE_SKILL);

      vi.mocked(mocks.policyEngine.evaluate).mockResolvedValue({
        allowed: false,
        code: "E_POLICY_ROLE_DENIED",
        reason: "Not allowed",
      } as any);

      const result = await engine.execute("skill.test.simple");

      expect(result.success).toBe(false);
      expect(result.error).toContain("Not allowed");
      expect(mocks.executor.execute).not.toHaveBeenCalled();
    });

    it("should support cancellation via AbortSignal", async () => {
      const longSkill: SkillDefinition = {
        skill_id: "skill.test.long",
        name: "Long Skill",
        description: "Skill with delay",
        version: "1.0.0",
        risk_level: "READ_ONLY",
        steps: [
          { id: "step1", capability_id: "tool.sensor.ultrasonic", params: {} },
          { id: "step2", capability_id: "tool.sensor.infrared", params: {}, delay_ms: 5000 },
        ],
      };

      engine.registerSkill(longSkill);
      const controller = new AbortController();

      // Abort after first step completes
      vi.mocked(mocks.executor.execute).mockImplementation(async () => {
        controller.abort();
        return makeSuccessResult({ ok: true });
      });

      const result = await engine.execute("skill.test.long", {}, controller.signal);

      expect(result.success).toBe(false);
      expect(result.error).toContain("cancelled");
    });
  });

  describe("state conditions", () => {
    it("should evaluate state conditions", async () => {
      const stateSkill: SkillDefinition = {
        skill_id: "skill.test.state_cond",
        name: "State Condition Test",
        description: "Conditional on state",
        version: "1.0.0",
        risk_level: "READ_ONLY",
        steps: [
          {
            id: "check_mode",
            capability_id: "tool.sensor.ultrasonic",
            params: {},
            condition: {
              type: "state",
              key: "mode",
              op: "==",
              value: "normal",
            },
          },
        ],
      };

      engine.registerSkill(stateSkill);

      // Default mode is "normal"
      const result = await engine.execute("skill.test.state_cond");
      expect(result.success).toBe(true);
      expect(mocks.executor.execute).toHaveBeenCalledTimes(1);
    });

    it("should skip step when state condition fails", async () => {
      const stateSkill: SkillDefinition = {
        skill_id: "skill.test.state_fail",
        name: "State Fail Test",
        description: "Conditional on state",
        version: "1.0.0",
        risk_level: "READ_ONLY",
        steps: [
          {
            id: "check_mode",
            capability_id: "tool.sensor.ultrasonic",
            params: {},
            condition: {
              type: "state",
              key: "mode",
              op: "==",
              value: "debug",
            },
          },
        ],
      };

      engine.registerSkill(stateSkill);

      const result = await engine.execute("skill.test.state_fail");
      expect(result.success).toBe(true);
      expect(result.results["check_mode"]).toEqual({ skipped: true, reason: "condition_not_met" });
      expect(mocks.executor.execute).not.toHaveBeenCalled();
    });
  });
});
