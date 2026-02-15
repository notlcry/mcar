/**
 * PromptBuilder unit tests.
 *
 * Tests:
 * - prompt includes memory context
 * - prompt includes state info (mode, session, apiStatus)
 * - prompt includes capability list
 * - prompt includes module health when provided
 */

import { describe, it, expect, vi } from "vitest";
import { PromptBuilder } from "../../src/agent/prompt-builder.js";
import type { ContextBuilder, SessionContext } from "../../src/orchestrator/context-builder.js";

function createMockContextBuilder(overrides: Partial<SessionContext> = {}): ContextBuilder {
  const defaultCtx: SessionContext = {
    memories: [],
    stateSnapshot: {
      session: "IDLE",
      mode: "normal",
      apiStatus: "online",
      obstacle: false,
      batteryLevel: 0.85,
      safetyLock: false,
    },
    capabilities: [],
    ...overrides,
  };
  return {
    build: vi.fn().mockReturnValue(defaultCtx),
    setWatchdog: vi.fn(),
  } as any;
}

describe("PromptBuilder", () => {
  it("should include memory context in prompt", () => {
    const ctx = createMockContextBuilder({
      memories: ["[preference] User likes slow speed", "[rule] Never exceed 50"],
    });
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).toContain("## Remembered Context");
    expect(prompt).toContain("User likes slow speed");
    expect(prompt).toContain("Never exceed 50");
  });

  it("should include state information in prompt", () => {
    const ctx = createMockContextBuilder({
      stateSnapshot: {
        session: "IDLE",
        mode: "kid",
        apiStatus: "degraded",
        obstacle: true,
        batteryLevel: 0.42,
        safetyLock: true,
        lastAction: "motion.forward",
      },
    });
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).toContain("Mode: kid");
    expect(prompt).toContain("API Status: degraded");
    expect(prompt).toContain("Battery: 42%");
    expect(prompt).toContain("Safety lock: true");
    expect(prompt).toContain("Last action: motion.forward");
  });

  it("should include capabilities in prompt", () => {
    const ctx = createMockContextBuilder({
      capabilities: [
        "Voice Recognize (tool.voice.recognize) [READ_ONLY]",
        "Motion Forward (tool.motion.forward) [DANGEROUS]",
      ],
    });
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).toContain("## Available Capabilities");
    expect(prompt).toContain("tool.voice.recognize");
    expect(prompt).toContain("tool.motion.forward");
  });

  it("should include module health when watchdog provides it", () => {
    const ctx = createMockContextBuilder({
      moduleHealth: ["mock: OK", "voice: OK", "motion: DOWN (restarts: 2)"],
    });
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).toContain("## Module Health");
    expect(prompt).toContain("mock: OK");
    expect(prompt).toContain("motion: DOWN (restarts: 2)");
  });

  it("should not include module health section when not provided", () => {
    const ctx = createMockContextBuilder();
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).not.toContain("## Module Health");
  });

  it("should always include base prompt and memory proposal instructions", () => {
    const ctx = createMockContextBuilder();
    const builder = new PromptBuilder(ctx);
    const prompt = builder.build();

    expect(prompt).toContain("You are mcar");
    expect(prompt).toContain("## Memory Management");
    expect(prompt).toContain("tool.memory.propose");
  });
});
