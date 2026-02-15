/**
 * CapabilityExecutor unit tests.
 *
 * Tests:
 * - Parameter validation (AJV)
 * - Rate limiting
 * - Cooldown
 * - Idempotency (IDEMPOTENT + DEDUP_ONLY)
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { CapabilityExecutor } from "../../src/capability/executor.js";
import type { CapabilityRegistry } from "../../src/capability/registry.js";
import type { CapabilitySpec, RegisteredCapability } from "../../src/capability/types.js";
import { IpcInvokeError } from "../../src/ipc/module-proxy.js";

function makeSpec(overrides: Partial<CapabilitySpec> = {}): CapabilitySpec {
  return {
    capability_id: "tool.test",
    name: "Test",
    type: "tool",
    version: "1.0.0",
    description: "test",
    risk_level: "READ_ONLY",
    inputs_schema: {
      type: "object",
      properties: {
        text: { type: "string", minLength: 1 },
      },
      required: ["text"],
      additionalProperties: false,
    },
    outputs_schema: {},
    constraints: { timeout_ms: 5000 },
    required_state_predicates: [],
    permissions: {
      roles_allowed: ["user"],
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

function makeMockRegistry(
  spec: CapabilitySpec,
  invokeResult: Record<string, unknown> = { ok: true }
): CapabilityRegistry {
  return {
    getCapability: (id: string): RegisteredCapability | undefined => {
      if (id === spec.capability_id) {
        return { spec, moduleId: "test-module" };
      }
      return undefined;
    },
    getProxy: () => ({
      invoke: async () => invokeResult,
    }),
  } as unknown as CapabilityRegistry;
}

describe("CapabilityExecutor", () => {
  it("should reject invalid parameters", async () => {
    const spec = makeSpec();
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    const result = await executor.execute("tool.test", { text: "" }); // minLength: 1
    expect(result.success).toBe(false);
    expect(result.error?.code).toBe("E_INPUT_SCHEMA");
  });

  it("should accept valid parameters and invoke", async () => {
    const spec = makeSpec();
    const registry = makeMockRegistry(spec, { ok: true, echo: "hi" });
    const executor = new CapabilityExecutor(registry);

    const result = await executor.execute("tool.test", { text: "hi" });
    expect(result.success).toBe(true);
    expect(result.data?.echo).toBe("hi");
  });

  it("should return E_NOT_FOUND for unknown capability", async () => {
    const spec = makeSpec();
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    const result = await executor.execute("tool.unknown", {});
    expect(result.success).toBe(false);
    expect(result.error?.code).toBe("E_NOT_FOUND");
  });

  it("should enforce rate limit", async () => {
    const spec = makeSpec({
      constraints: {
        timeout_ms: 5000,
        rate_limit: { qps: 1, burst: 1 },
      },
    });
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    // First call should succeed
    const result1 = await executor.execute("tool.test", { text: "a" });
    expect(result1.success).toBe(true);

    // Second immediate call should be rate limited
    const result2 = await executor.execute("tool.test", { text: "b" });
    expect(result2.success).toBe(false);
    expect(result2.error?.code).toBe("E_RATE_LIMITED");
  });

  it("should enforce cooldown", async () => {
    const spec = makeSpec({
      constraints: {
        timeout_ms: 5000,
        cooldown_ms: 500,
      },
    });
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    const result1 = await executor.execute("tool.test", { text: "a" });
    expect(result1.success).toBe(true);

    // Immediate second call should hit cooldown
    const result2 = await executor.execute("tool.test", { text: "b" });
    expect(result2.success).toBe(false);
    expect(result2.error?.code).toBe("E_COOLDOWN_ACTIVE");
  });

  it("should return cached result for IDEMPOTENT mode", async () => {
    let invokeCount = 0;
    const spec = makeSpec({
      idempotency: { mode: "IDEMPOTENT", key_fields: ["text"], ttl_ms: 5000 },
    });
    const registry = {
      getCapability: (id: string) => ({ spec, moduleId: "m" }),
      getProxy: () => ({
        invoke: async () => {
          invokeCount++;
          return { ok: true, count: invokeCount };
        },
      }),
    } as unknown as CapabilityRegistry;
    const executor = new CapabilityExecutor(registry);

    const r1 = await executor.execute("tool.test", { text: "hello" });
    expect(r1.success).toBe(true);
    expect(invokeCount).toBe(1);

    // Same params → should return cached
    const r2 = await executor.execute("tool.test", { text: "hello" });
    expect(r2.success).toBe(true);
    expect(invokeCount).toBe(1); // NOT incremented
    expect(r2.data?.count).toBe(1);
  });

  it("should reject duplicate for DEDUP_ONLY mode", async () => {
    const spec = makeSpec({
      idempotency: { mode: "DEDUP_ONLY", key_fields: ["text"], ttl_ms: 5000 },
    });
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    const r1 = await executor.execute("tool.test", { text: "hello" });
    expect(r1.success).toBe(true);

    const r2 = await executor.execute("tool.test", { text: "hello" });
    expect(r2.success).toBe(false);
    expect(r2.error?.code).toBe("E_DUPLICATE");
  });

  // ─── Concurrency control ──────────────────────────────────

  it("should enforce max_in_flight limit", async () => {
    let activeCount = 0;
    let peakCount = 0;
    const spec = makeSpec({
      capability_id: "tool.conc",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1 },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.conc" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          activeCount++;
          peakCount = Math.max(peakCount, activeCount);
          // Simulate some async work
          await new Promise((r) => setTimeout(r, 50));
          activeCount--;
          return { ok: true };
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);

    // Launch two concurrent executions
    const [r1, r2] = await Promise.all([
      executor.execute("tool.conc", {}),
      executor.execute("tool.conc", {}),
    ]);

    // One should succeed, the other should be rejected
    const results = [r1, r2];
    const successes = results.filter((r) => r.success);
    const failures = results.filter((r) => !r.success);

    expect(successes).toHaveLength(1);
    expect(failures).toHaveLength(1);
    expect(failures[0].error?.code).toBe("E_CONCURRENCY");
    expect(failures[0].error?.retryable).toBe(true);
  });

  it("should enforce mutex_group across capabilities", async () => {
    const specA = makeSpec({
      capability_id: "tool.move_forward",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1, mutex_group: "motion" },
      },
      inputs_schema: {},
    });
    const specB = makeSpec({
      capability_id: "tool.move_backward",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1, mutex_group: "motion" },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) => {
        if (id === "tool.move_forward") return { spec: specA, moduleId: "m" };
        if (id === "tool.move_backward") return { spec: specB, moduleId: "m" };
        return undefined;
      },
      getProxy: () => ({
        invoke: async () => {
          await new Promise((r) => setTimeout(r, 50));
          return { ok: true };
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);

    // Launch two different capabilities in the same mutex group
    const [r1, r2] = await Promise.all([
      executor.execute("tool.move_forward", {}),
      executor.execute("tool.move_backward", {}),
    ]);

    const results = [r1, r2];
    const successes = results.filter((r) => r.success);
    const failures = results.filter((r) => !r.success);

    expect(successes).toHaveLength(1);
    expect(failures).toHaveLength(1);
    expect(failures[0].error?.code).toBe("E_CONCURRENCY");
    expect(failures[0].error?.message).toContain("Mutex group");
  });

  it("should release concurrency slot after execution completes", async () => {
    const spec = makeSpec({
      capability_id: "tool.serial",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1 },
      },
      inputs_schema: {},
    });
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    // First call
    const r1 = await executor.execute("tool.serial", {});
    expect(r1.success).toBe(true);

    // Second call after first completed — should succeed (slot released)
    const r2 = await executor.execute("tool.serial", {});
    expect(r2.success).toBe(true);
  });

  it("should release concurrency slot even on invoke failure", async () => {
    const spec = makeSpec({
      capability_id: "tool.failing",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1 },
      },
      inputs_schema: {},
    });

    let callCount = 0;
    const registry = {
      getCapability: (id: string) =>
        id === "tool.failing" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          if (callCount === 1) throw new Error("invoke failed");
          return { ok: true };
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);

    // First call fails
    const r1 = await executor.execute("tool.failing", {});
    expect(r1.success).toBe(false);
    expect(r1.error?.code).toBe("E_INTERNAL");

    // Second call should succeed — slot was released despite error
    const r2 = await executor.execute("tool.failing", {});
    expect(r2.success).toBe(true);
  });

  // ─── Duration tracking ──────────────────────────────────

  it("should include duration_ms on successful execution", async () => {
    const spec = makeSpec({
      capability_id: "tool.duration",
      inputs_schema: {},
    });
    const registry = makeMockRegistry(spec);
    const executor = new CapabilityExecutor(registry);

    const result = await executor.execute("tool.duration", {});
    expect(result.success).toBe(true);
    expect(result.duration_ms).toBeDefined();
    expect(result.duration_ms).toBeGreaterThanOrEqual(0);
  });

  // ─── Retry policy ──────────────────────────────────────

  it("should retry on retriable error and succeed", async () => {
    let callCount = 0;
    const spec = makeSpec({
      capability_id: "tool.retry_ok",
      constraints: {
        timeout_ms: 5000,
        retry_policy: {
          retriable_errors: ["E_TIMEOUT"],
          max_retries: 2,
          backoff_ms: 10,
        },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.retry_ok" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          if (callCount < 2) throw new IpcInvokeError("E_TIMEOUT", "timeout");
          return { ok: true };
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);
    const result = await executor.execute("tool.retry_ok", {});
    expect(result.success).toBe(true);
    expect(callCount).toBe(2);
  });

  it("should return failure after retries exhausted", async () => {
    let callCount = 0;
    const spec = makeSpec({
      capability_id: "tool.retry_exhaust",
      constraints: {
        timeout_ms: 5000,
        retry_policy: {
          retriable_errors: ["E_TIMEOUT"],
          max_retries: 2,
          backoff_ms: 10,
        },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.retry_exhaust" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          throw new IpcInvokeError("E_TIMEOUT", "timeout");
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);
    const result = await executor.execute("tool.retry_exhaust", {});
    expect(result.success).toBe(false);
    expect(callCount).toBe(3); // 1 initial + 2 retries
  });

  it("should not retry non-retriable errors", async () => {
    let callCount = 0;
    const spec = makeSpec({
      capability_id: "tool.no_retry",
      constraints: {
        timeout_ms: 5000,
        retry_policy: {
          retriable_errors: ["E_TIMEOUT"],
          max_retries: 3,
          backoff_ms: 10,
        },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.no_retry" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          throw new IpcInvokeError("E_INTERNAL", "internal error");
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);
    const result = await executor.execute("tool.no_retry", {});
    expect(result.success).toBe(false);
    expect(callCount).toBe(1); // No retries
  });

  it("should not retry when no retry_policy is set", async () => {
    let callCount = 0;
    const spec = makeSpec({
      capability_id: "tool.no_policy",
      constraints: { timeout_ms: 5000 },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.no_policy" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          throw new IpcInvokeError("E_TIMEOUT", "timeout");
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);
    const result = await executor.execute("tool.no_policy", {});
    expect(result.success).toBe(false);
    expect(callCount).toBe(1);
  });

  it("should apply exponential backoff during retries", async () => {
    const delays: number[] = [];
    let callCount = 0;
    const spec = makeSpec({
      capability_id: "tool.backoff",
      constraints: {
        timeout_ms: 5000,
        retry_policy: {
          retriable_errors: ["E_TIMEOUT"],
          max_retries: 3,
          backoff_ms: 50,
        },
      },
      inputs_schema: {},
    });

    const registry = {
      getCapability: (id: string) =>
        id === "tool.backoff" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          const now = Date.now();
          if (callCount > 0) {
            delays.push(now);
          }
          callCount++;
          throw new IpcInvokeError("E_TIMEOUT", "timeout");
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);
    const start = Date.now();
    await executor.execute("tool.backoff", {});

    expect(callCount).toBe(4); // 1 + 3 retries
    // Total elapsed should be at least backoff_ms*(1+2+4) = 50+100+200 = 350ms
    // But we allow some tolerance
    const totalElapsed = Date.now() - start;
    expect(totalElapsed).toBeGreaterThanOrEqual(300);
  });

  it("should release concurrency slot after retries exhausted", async () => {
    const spec = makeSpec({
      capability_id: "tool.retry_conc",
      constraints: {
        timeout_ms: 5000,
        concurrency: { max_in_flight: 1 },
        retry_policy: {
          retriable_errors: ["E_TIMEOUT"],
          max_retries: 1,
          backoff_ms: 10,
        },
      },
      inputs_schema: {},
    });

    let callCount = 0;
    const registry = {
      getCapability: (id: string) =>
        id === "tool.retry_conc" ? { spec, moduleId: "m" } : undefined,
      getProxy: () => ({
        invoke: async () => {
          callCount++;
          if (callCount <= 2) throw new IpcInvokeError("E_TIMEOUT", "timeout");
          return { ok: true };
        },
      }),
    } as unknown as CapabilityRegistry;

    const executor = new CapabilityExecutor(registry);

    // First call: retries exhausted (2 attempts, both fail)
    const r1 = await executor.execute("tool.retry_conc", {});
    expect(r1.success).toBe(false);

    // Second call should succeed — concurrency slot was released
    const r2 = await executor.execute("tool.retry_conc", {});
    expect(r2.success).toBe(true);
  });
});
