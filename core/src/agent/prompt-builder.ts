/**
 * PromptBuilder — assembles the system prompt from:
 * - Base identity and behavior rules
 * - Injected memory context (via ContextBuilder)
 * - Available capabilities summary (via ContextBuilder)
 * - Current state snapshot (via ContextBuilder)
 * - Module health status (via ContextBuilder, when watchdog provided)
 * - Memory proposal instructions
 */

import type { ContextBuilder, SessionContext } from "../orchestrator/context-builder.js";

const BASE_PROMPT = `You are mcar, a robot assistant running on a Raspberry Pi.
You interact through voice (primary) and text. Be concise, friendly, and helpful.

## Core Rules
- Safety first: never override safety gates or skip confirmations for dangerous actions.
- If a tool returns a denial or confirmation request, relay it faithfully to the user.
- When unsure, ask the user rather than guessing.
- You can combine multiple tool calls to complete a task.
- Report tool results naturally in conversational language.

## Emergency Stop
- If the user says "stop", "halt", "emergency", or similar, the system will trigger an emergency stop.
- During safety lock, only READ_ONLY operations are available.
`;

const MEMORY_PROPOSAL_PROMPT = `
## Memory Management
You can propose to remember important information about the user. Use the memory tools when:
- The user shares a preference (e.g., "I like slow speeds", "Call me Alice")
- The user states a fact worth remembering (e.g., "My room is on the 2nd floor")
- The user sets a rule (e.g., "Never go faster than 30")
- You detect a recurring pattern worth noting

When proposing a memory:
- Use tool.memory.propose with a clear summary and appropriate type
- The user will be asked to confirm before the memory is saved
- Be conservative: only propose memories for clearly important information
- Use tool.memory.list to check for duplicates before proposing

Available memory types: preference, fact, rule, device, location, task, incident, skill_state, other
`;

export class PromptBuilder {
  constructor(
    private readonly contextBuilder: ContextBuilder
  ) {}

  build(): string {
    const ctx = this.contextBuilder.build();
    return this.assemble(ctx);
  }

  private assemble(ctx: SessionContext): string {
    const parts: string[] = [BASE_PROMPT];

    // Inject memory proposal instructions
    parts.push(MEMORY_PROPOSAL_PROMPT);

    // Inject memory context
    if (ctx.memories.length > 0) {
      parts.push("## Remembered Context");
      for (const mem of ctx.memories) {
        parts.push(`- ${mem}`);
      }
      parts.push("");
    }

    // Inject state snapshot
    const state = ctx.stateSnapshot;
    parts.push("## Current State");
    parts.push(`- Session: ${state.session ?? "unknown"}`);
    parts.push(`- Mode: ${state.mode ?? "normal"}`);
    parts.push(`- API Status: ${state.apiStatus ?? "unknown"}`);
    parts.push(`- Obstacle detected: ${state.obstacle ?? false}`);
    parts.push(`- Battery: ${Math.round(((state.batteryLevel as number) ?? 1) * 100)}%`);
    parts.push(`- Safety lock: ${state.safetyLock ?? false}`);
    if (state.lastAction) {
      parts.push(`- Last action: ${state.lastAction}`);
    }
    parts.push("");

    // Inject capability summary
    if (ctx.capabilities.length > 0) {
      parts.push("## Available Capabilities");
      for (const cap of ctx.capabilities) {
        parts.push(`- ${cap}`);
      }
      parts.push("");
    }

    // Inject module health status (when watchdog is configured)
    if (ctx.moduleHealth && ctx.moduleHealth.length > 0) {
      parts.push("## Module Health");
      for (const h of ctx.moduleHealth) {
        parts.push(`- ${h}`);
      }
      parts.push("");
    }

    return parts.join("\n");
  }
}
