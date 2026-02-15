/**
 * VoiceLoop unit tests.
 *
 * Tests:
 * - Wake word event triggers ASR → dispatch → TTS flow
 * - Stop word event triggers emergency stop
 * - Ignored when not in IDLE state
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { VoiceLoop } from "../../src/orchestrator/voice-loop.js";
import { SessionController } from "../../src/orchestrator/session-controller.js";
import { ActionDispatcher } from "../../src/orchestrator/action-dispatcher.js";
import { StopHandler } from "../../src/safety/stop-handler.js";
import { StateService } from "../../src/state/state-service.js";
import type { AuditLogger } from "../../src/audit/audit-logger.js";
import type { ModuleEvent } from "../../src/ipc/protocol.js";

// Mock bridge
const mockBridge = {
  broadcastStop: vi.fn(async () => {}),
  onEvent: vi.fn(() => () => {}),
} as any;

// Mock executor
const mockExecutor = {
  execute: vi.fn(async (capId: string, params: Record<string, unknown>) => {
    if (capId === "tool.voice.recognize") {
      return { success: true, data: { ok: true, text: "Hello", confidence: 0.9 } };
    }
    return { success: true, data: { ok: true } };
  }),
} as any;

// Mock agent runtime
const mockAgent = {
  prompt: vi.fn(async () => {}),
  subscribe: vi.fn(() => () => {}),
} as any;

// Mock audit logger
const mockAudit: AuditLogger = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  getEntries: vi.fn(() => []),
} as any;

/** Helper: flush microtask queue */
function flushAsync(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 10));
}

describe("VoiceLoop", () => {
  let stateService: StateService;
  let stopHandler: StopHandler;
  let session: SessionController;
  let dispatcher: ActionDispatcher;
  let voiceLoop: VoiceLoop;

  beforeEach(() => {
    vi.clearAllMocks();

    stateService = new StateService();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 2000 });
    session = new SessionController(stateService, stopHandler);
    dispatcher = new ActionDispatcher(session, mockAgent, mockAudit, stopHandler);

    voiceLoop = new VoiceLoop(
      session,
      dispatcher,
      mockBridge,
      mockExecutor,
      stopHandler,
      stateService,
      mockAudit
    );
  });

  it("should subscribe to bridge events on start", () => {
    voiceLoop.start();
    expect(mockBridge.onEvent).toHaveBeenCalled();
    voiceLoop.stop();
  });

  it("should unsubscribe on stop", () => {
    const unsub = vi.fn();
    mockBridge.onEvent.mockReturnValue(unsub);
    voiceLoop.start();
    voiceLoop.stop();
    expect(unsub).toHaveBeenCalled();
  });

  it("should handle wake word event and complete voice flow", async () => {
    // Capture the event handler
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    // Mock dispatcher dispatch to return a response
    const dispatchSpy = vi.spyOn(dispatcher, "dispatch").mockResolvedValue("I am mcar!");

    voiceLoop.start();
    await flushAsync(); // Let startListening complete

    // Clear calls from initialization
    mockExecutor.execute.mockClear();

    expect(eventHandler).not.toBeNull();

    // Simulate wake word event
    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // Collect all capability IDs called
    const calledCapIds = mockExecutor.execute.mock.calls.map((c: any[]) => c[0]);

    // Should have called display expression (listening), recognize, display (thinking), dispatch, display (speaking), synthesize, display (neutral)
    expect(calledCapIds).toContain("tool.display.show_expression");
    expect(calledCapIds).toContain("tool.voice.recognize");
    expect(calledCapIds).toContain("tool.voice.synthesize");

    // Should have dispatched text to agent
    expect(dispatchSpy).toHaveBeenCalledWith("Hello");

    voiceLoop.stop();
  });

  it("should handle stop word event and trigger emergency stop", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    voiceLoop.start();
    await flushAsync();

    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.stop_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // Should have triggered stop
    expect(mockBridge.broadcastStop).toHaveBeenCalledWith("voice");

    voiceLoop.stop();
  });

  it("should ignore wake word when not IDLE", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    voiceLoop.start();
    await flushAsync();

    // Put system in THINKING state
    stateService.setSessionState("THINKING");

    const dispatchSpy = vi.spyOn(dispatcher, "dispatch");

    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // Should NOT have dispatched
    expect(dispatchSpy).not.toHaveBeenCalled();

    voiceLoop.stop();
  });

  it("should not TTS in mute mode", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    vi.spyOn(dispatcher, "dispatch").mockResolvedValue("Response");

    stateService.setMode("mute");
    voiceLoop.start();
    await flushAsync();
    mockExecutor.execute.mockClear();

    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // Should NOT have called synthesize
    const synthCalls = mockExecutor.execute.mock.calls.filter(
      (c: any[]) => c[0] === "tool.voice.synthesize"
    );
    expect(synthCalls).toHaveLength(0);

    voiceLoop.stop();
  });
});
