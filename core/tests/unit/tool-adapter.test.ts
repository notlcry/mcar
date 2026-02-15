/**
 * ToolAdapter unit tests.
 *
 * Tests:
 * - CapabilitySpec → AgentTool conversion
 * - Policy denial returns friendly text instead of throwing
 * - Confirmation request returns hint text
 */

import { describe, it, expect, beforeEach } from "vitest";
import { capabilityToTool } from "../../src/agent/tool-adapter.js";
import { AuditLogger } from "../../src/audit/audit-logger.js";
import type { CapabilitySpec } from "../../src/capability/types.js";
import type { CapabilityExecutor } from "../../src/capability/executor.js";
import type { PolicyEngine } from "../../src/safety/policy-engine.js";

function makeSpec(overrides: Partial<CapabilitySpec> = {}): CapabilitySpec {
  return {
    capability_id: "tool.test.echo",
    name: "Echo",
    type: "tool",
    version: "1.0.0",
    description: "Echo test tool",
    risk_level: "READ_ONLY",
    inputs_schema: {
      type: "object",
      properties: {
        text: { type: "string" },
      },
      required: ["text"],
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

describe("ToolAdapter", () => {
  let auditLogger: AuditLogger;

  beforeEach(() => {
    auditLogger = new AuditLogger();
  });

  it("should convert CapabilitySpec to AgentTool with correct metadata", () => {
    const spec = makeSpec();
    const mockExecutor = {} as CapabilityExecutor;
    const mockPolicy = {
      evaluate: async () => ({ allowed: true as const }),
    } as unknown as PolicyEngine;

    const tool = capabilityToTool(spec, mockExecutor, mockPolicy, auditLogger);

    expect(tool.name).toBe("tool.test.echo");
    expect(tool.label).toBe("Echo");
    expect(tool.description).toContain("READ_ONLY");
  });

  it("should return denial text when policy denies", async () => {
    const spec = makeSpec();
    const mockExecutor = {} as CapabilityExecutor;
    const mockPolicy = {
      evaluate: async () => ({
        allowed: false as const,
        code: "E_STATE_ESTOP",
        reason: "Emergency stop active",
        userMessage: "System is stopped",
        retryable: true,
      }),
    } as unknown as PolicyEngine;

    const tool = capabilityToTool(spec, mockExecutor, mockPolicy, auditLogger);
    const result = await tool.execute("call-1", { text: "hello" });

    expect(result.content[0].type).toBe("text");
    expect((result.content[0] as any).text).toContain("System is stopped");
    expect(result.details).toHaveProperty("denied", true);
  });

  it("should return confirmation text when policy requires confirm", async () => {
    const spec = makeSpec();
    const mockExecutor = {} as CapabilityExecutor;
    const mockPolicy = {
      evaluate: async () => ({
        allowed: "confirm" as const,
        reason: "Dangerous action",
        confirmHint: "Are you sure?",
      }),
    } as unknown as PolicyEngine;

    const tool = capabilityToTool(spec, mockExecutor, mockPolicy, auditLogger);
    const result = await tool.execute("call-2", { text: "hello" });

    expect((result.content[0] as any).text).toContain("confirmation");
    expect(result.details).toHaveProperty("needsConfirmation", true);
  });

  it("should call executor and return formatted result on success", async () => {
    const spec = makeSpec();
    const mockExecutor = {
      execute: async () => ({
        success: true,
        data: { ok: true, echo: "hello" },
      }),
    } as unknown as CapabilityExecutor;
    const mockPolicy = {
      evaluate: async () => ({ allowed: true as const }),
    } as unknown as PolicyEngine;

    const tool = capabilityToTool(spec, mockExecutor, mockPolicy, auditLogger);
    const result = await tool.execute("call-3", { text: "hello" });

    const text = (result.content[0] as any).text;
    const parsed = JSON.parse(text);
    expect(parsed.ok).toBe(true);
    expect(parsed.echo).toBe("hello");
  });
});
