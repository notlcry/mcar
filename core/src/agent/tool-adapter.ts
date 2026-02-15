/**
 * ToolAdapter — converts CapabilitySpec → pi-agent-core AgentTool.
 *
 * Safety policy is injected inside the tool's execute function,
 * since pi-agent-core has no native pre-hook mechanism.
 *
 * Also builds virtual memory tools (propose, list) for implicit memory.
 */

import { Type, type TSchema } from "@sinclair/typebox";
import type { AgentTool, AgentToolResult } from "@mariozechner/pi-agent-core";
import type { CapabilitySpec } from "../capability/types.js";
import type { CapabilityExecutor, ExecutionResult } from "../capability/executor.js";
import type { PolicyEngine } from "../safety/policy-engine.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import { redactPayload } from "../audit/redactor.js";
import type { MemoryService } from "../memory/memory-service.js";
import type { MemoryType } from "../memory/types.js";
import type { IncidentRecorder } from "../observability/incident-recorder.js";
import { v4 as uuid } from "uuid";

/**
 * Convert a JSON Schema object to a TypeBox TSchema.
 * Handles the common cases used in capability specs.
 */
function jsonSchemaToTypeBox(schema: Record<string, unknown>): TSchema {
  if (!schema || schema.type !== "object") {
    return Type.Object({});
  }

  const properties = (schema.properties ?? {}) as Record<string, Record<string, unknown>>;
  const required = (schema.required ?? []) as string[];
  const props: Record<string, TSchema> = {};

  for (const [key, propSchema] of Object.entries(properties)) {
    const isRequired = required.includes(key);
    let field: TSchema;

    switch (propSchema.type) {
      case "string":
        field = Type.String({ description: propSchema.description as string | undefined });
        break;
      case "number":
        field = Type.Number({
          description: propSchema.description as string | undefined,
          minimum: propSchema.minimum as number | undefined,
          maximum: propSchema.maximum as number | undefined,
        });
        break;
      case "integer":
        field = Type.Integer({
          description: propSchema.description as string | undefined,
          minimum: propSchema.minimum as number | undefined,
          maximum: propSchema.maximum as number | undefined,
        });
        break;
      case "boolean":
        field = Type.Boolean({ description: propSchema.description as string | undefined });
        break;
      case "array":
        field = Type.Array(Type.Unknown());
        break;
      default:
        field = Type.Unknown();
    }

    props[key] = isRequired ? field : Type.Optional(field);
  }

  return Type.Object(props);
}

/**
 * Convert a single CapabilitySpec into an AgentTool.
 */
export function capabilityToTool(
  spec: CapabilitySpec,
  executor: CapabilityExecutor,
  policyEngine: PolicyEngine,
  auditLogger: AuditLogger,
  incidentRecorder?: IncidentRecorder
): AgentTool {
  return {
    name: spec.capability_id,
    label: spec.name,
    description: `${spec.description} [risk: ${spec.risk_level}]`,
    parameters: jsonSchemaToTypeBox(spec.inputs_schema),
    execute: async (toolCallId, params, signal, onUpdate) => {
      const traceId = uuid();

      const redactionRules = spec.observability.redaction;

      auditLogger.info(traceId, "tool.invoke.start", {
        capability_id: spec.capability_id,
        params: spec.observability.log_inputs
          ? redactPayload(params as Record<string, unknown>, redactionRules)
          : "[redacted]",
      });

      // Policy check inside execute — the only injection point
      const decision = await policyEngine.evaluate(spec, params as Record<string, unknown>);

      if (decision.allowed === false) {
        auditLogger.warn(traceId, "tool.invoke.denied", {
          capability_id: spec.capability_id,
          code: decision.code,
          reason: decision.reason,
        });
        return {
          content: [{ type: "text", text: decision.userMessage ?? decision.reason }],
          details: { denied: true, code: decision.code },
        };
      }

      if (decision.allowed === "confirm") {
        auditLogger.info(traceId, "tool.invoke.confirm_required", {
          capability_id: spec.capability_id,
          reason: decision.reason,
        });
        return {
          content: [
            {
              type: "text",
              text: `This action requires confirmation: ${decision.reason}. ${decision.confirmHint ?? "Please confirm to proceed."}`,
            },
          ],
          details: { needsConfirmation: true, reason: decision.reason },
        };
      }

      // Execute via CapabilityExecutor (handles validation, rate limit, idempotency, IPC)
      const result = await executor.execute(spec.capability_id, params as Record<string, unknown>);

      if (result.success) {
        auditLogger.info(traceId, "tool.invoke.success", {
          capability_id: spec.capability_id,
          result: spec.observability.log_outputs
            ? redactPayload(result.data ?? {}, redactionRules)
            : "[redacted]",
        });

        return {
          content: [{ type: "text", text: JSON.stringify(result.data) }],
          details: result.data ?? {},
        };
      }

      auditLogger.error(traceId, "tool.invoke.error", {
        capability_id: spec.capability_id,
        error: result.error,
      });

      incidentRecorder?.record({
        category: "tool_error",
        error_code: result.error?.code ?? "E_INTERNAL",
        message: result.error?.message ?? "Unknown error",
        capability_id: spec.capability_id,
      });

      throw new Error(result.error?.message ?? "Unknown error");
    },
  };
}

/**
 * Build virtual memory tools for agent to propose/query memories.
 */
export function buildMemoryTools(
  memoryService: MemoryService,
  auditLogger: AuditLogger
): AgentTool[] {
  const proposeTool: AgentTool = {
    name: "tool.memory.propose",
    label: "Propose Memory",
    description: "Propose a new memory entry for the user to confirm. The memory will only be saved after the user confirms.",
    parameters: Type.Object({
      type: Type.String({ description: "Memory type: preference, fact, rule, device, location, task, incident, skill_state, other" }),
      summary: Type.String({ description: "Brief human-readable summary of the memory" }),
      content: Type.Optional(Type.String({ description: "Detailed content (JSON string)" })),
    }),
    execute: async (toolCallId, params) => {
      const memType = (params as any).type as string;
      const summary = (params as any).summary as string;

      auditLogger.info("memory", "memory.propose", { type: memType, summary });

      // Return a confirmation prompt — the actual saving happens
      // when the user confirms through ActionDispatcher
      return {
        content: [
          {
            type: "text",
            text: `I'd like to remember: "${summary}" (${memType}). Is that okay?`,
          },
        ],
        details: {
          needsConfirmation: true,
          memoryProposal: {
            type: memType,
            summary,
            content: (params as any).content,
          },
        },
      };
    },
  };

  const deleteTool: AgentTool = {
    name: "tool.memory.delete",
    label: "Delete Memory",
    description: "Delete a specific memory by its ID. Use tool.memory.list first to find the ID.",
    parameters: Type.Object({
      id: Type.String({ description: "The memory ID to delete" }),
    }),
    execute: async (toolCallId, params) => {
      const id = (params as any).id as string;
      const entry = memoryService.getById(id);

      if (!entry) {
        return {
          content: [{ type: "text", text: `Memory with ID "${id}" not found.` }],
          details: { success: false },
        };
      }

      const deleted = memoryService.delete(id);
      auditLogger.info("memory", "memory.delete", { id, summary: entry.summary });

      return {
        content: [
          { type: "text", text: deleted ? `Memory deleted: "${entry.summary}"` : "Failed to delete memory." },
        ],
        details: { success: deleted },
      };
    },
  };

  const clearTool: AgentTool = {
    name: "tool.memory.clear",
    label: "Clear Memories",
    description: "Clear all memories of a specific type. Requires confirmation.",
    parameters: Type.Object({
      type: Type.String({ description: "Memory type to clear: preference, fact, rule, device, location, task, incident, skill_state, other" }),
    }),
    execute: async (toolCallId, params) => {
      const memType = (params as any).type as MemoryType;

      auditLogger.info("memory", "memory.clear_request", { type: memType });

      return {
        content: [
          {
            type: "text",
            text: `Are you sure you want to clear all "${memType}" memories? This cannot be undone.`,
          },
        ],
        details: {
          needsConfirmation: true,
          clearType: memType,
        },
      };
    },
  };

  const listTool: AgentTool = {
    name: "tool.memory.list",
    label: "List Memories",
    description: "List existing memories to check for duplicates or retrieve information.",
    parameters: Type.Object({
      type: Type.Optional(Type.String({ description: "Filter by memory type" })),
    }),
    execute: async (toolCallId, params) => {
      const typeFilter = (params as any).type as string | undefined;
      const types = typeFilter ? [typeFilter as MemoryType] : undefined;
      const summaries = memoryService.listSummaries(types);

      return {
        content: [
          {
            type: "text",
            text: summaries.length > 0
              ? summaries.map((s) => `[${s.type}] ${s.summary}`).join("\n")
              : "No memories found.",
          },
        ],
        details: { memories: summaries },
      };
    },
  };

  return [proposeTool, deleteTool, clearTool, listTool];
}

/**
 * Convert all registered capabilities into AgentTools.
 */
export function buildToolsFromRegistry(
  capabilities: Array<{ spec: CapabilitySpec; moduleId: string }>,
  executor: CapabilityExecutor,
  policyEngine: PolicyEngine,
  auditLogger: AuditLogger,
  memoryService?: MemoryService,
  incidentRecorder?: IncidentRecorder
): AgentTool[] {
  const tools = capabilities.map((c) =>
    capabilityToTool(c.spec, executor, policyEngine, auditLogger, incidentRecorder)
  );

  // Add memory tools if memoryService is available
  if (memoryService) {
    tools.push(...buildMemoryTools(memoryService, auditLogger));
  }

  return tools;
}
