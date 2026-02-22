/**
 * VoiceLoop unit tests.
 *
 * Tests:
 * - Wake word event triggers multi-turn ASR → dispatch → TTS flow
 * - Conversation ends on ASR timeout (no input)
 * - Multi-turn: multiple exchanges without re-triggering wake word
 * - Stop word event triggers emergency stop
 * - Ignored when not in IDLE state
 * - Wake word detection paused during conversation, resumed after
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

// Mock executor — returns text once then silence (to exit the multi-turn loop)
function createMockExecutor(recognizeResponses?: Array<{ text?: string; is_stop_word?: boolean }>) {
  let recognizeCallIndex = 0;
  const responses = recognizeResponses ?? [{ text: "Hello" }];

  return {
    execute: vi.fn(async (capId: string, _params: Record<string, unknown>) => {
      if (capId === "tool.voice.recognize") {
        const resp = responses[recognizeCallIndex] ?? {}; // default: no text (timeout)
        recognizeCallIndex++;
        if (resp.text) {
          return { success: true, data: { ok: true, text: resp.text, confidence: 0.9, is_stop_word: resp.is_stop_word } };
        }
        return { success: true, data: { ok: true } }; // no text = ASR timeout
      }
      return { success: true, data: { ok: true } };
    }),
  } as any;
}

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

  beforeEach(() => {
    vi.clearAllMocks();

    stateService = new StateService();
    stopHandler = new StopHandler(mockBridge, { estopCooldownMs: 2000 });
    session = new SessionController(stateService, stopHandler);
    dispatcher = new ActionDispatcher(session, mockAgent, mockAudit, stopHandler);
  });

  function createVoiceLoop(mockExecutor: any): VoiceLoop {
    return new VoiceLoop(
      session,
      dispatcher,
      mockBridge,
      mockExecutor,
      stopHandler,
      stateService,
      mockAudit
    );
  }

  it("should subscribe to bridge events on start", () => {
    const voiceLoop = createVoiceLoop(createMockExecutor());
    voiceLoop.start();
    expect(mockBridge.onEvent).toHaveBeenCalled();
    voiceLoop.stop();
  });

  it("should unsubscribe on stop", () => {
    const unsub = vi.fn();
    mockBridge.onEvent.mockReturnValue(unsub);
    const voiceLoop = createVoiceLoop(createMockExecutor());
    voiceLoop.start();
    voiceLoop.stop();
    expect(unsub).toHaveBeenCalled();
  });

  it("should handle single-turn voice flow (ASR timeout after first response)", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    // One successful recognize, then timeout (no text)
    const mockExecutor = createMockExecutor([{ text: "Hello" }]);
    const dispatchSpy = vi.spyOn(dispatcher, "dispatch").mockResolvedValue("I am mcar!");
    const voiceLoop = createVoiceLoop(mockExecutor);

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

    const calledCapIds = mockExecutor.execute.mock.calls.map((c: any[]) => c[0]);

    expect(calledCapIds).toContain("tool.display.show_expression");
    expect(calledCapIds).toContain("tool.voice.recognize");
    expect(calledCapIds).toContain("tool.voice.synthesize");
    expect(dispatchSpy).toHaveBeenCalledWith("Hello");

    // Should return to IDLE after conversation ends
    expect(session.current).toBe("IDLE");

    voiceLoop.stop();
  });

  it("should support multi-turn conversation without re-triggering wake word", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    // Three turns of conversation, then timeout
    const mockExecutor = createMockExecutor([
      { text: "你好" },
      { text: "今天天气怎么样" },
      { text: "谢谢" },
      // 4th call: no text → timeout → exit loop
    ]);

    const dispatchSpy = vi.spyOn(dispatcher, "dispatch").mockResolvedValue("回复");
    const voiceLoop = createVoiceLoop(mockExecutor);

    voiceLoop.start();
    await flushAsync();
    mockExecutor.execute.mockClear();

    // Single wake word event triggers multi-turn
    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // dispatch should have been called 3 times (once per turn)
    expect(dispatchSpy).toHaveBeenCalledTimes(3);
    expect(dispatchSpy).toHaveBeenCalledWith("你好");
    expect(dispatchSpy).toHaveBeenCalledWith("今天天气怎么样");
    expect(dispatchSpy).toHaveBeenCalledWith("谢谢");

    // recognize called 4 times (3 successful + 1 timeout)
    const recognizeCalls = mockExecutor.execute.mock.calls.filter(
      (c: any[]) => c[0] === "tool.voice.recognize"
    );
    expect(recognizeCalls).toHaveLength(4);

    // Should return to IDLE
    expect(session.current).toBe("IDLE");

    // session.end audit log should show 3 turns
    const sessionEndCalls = (mockAudit.info as any).mock.calls.filter(
      (c: any[]) => c[1] === "session.end"
    );
    expect(sessionEndCalls).toHaveLength(1);
    expect(sessionEndCalls[0][2]).toEqual({ turns: 3 });

    voiceLoop.stop();
  });

  it("should pause wake word detection during conversation and resume after", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    const mockExecutor = createMockExecutor([{ text: "Hi" }]);
    vi.spyOn(dispatcher, "dispatch").mockResolvedValue("Hello!");
    const voiceLoop = createVoiceLoop(mockExecutor);

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

    const calledCapIds = mockExecutor.execute.mock.calls.map((c: any[]) => c[0]);

    // listen_stop called at start of conversation, listen_start called at end
    expect(calledCapIds.indexOf("tool.voice.listen_stop")).toBeLessThan(
      calledCapIds.indexOf("tool.voice.recognize")
    );

    // listen_start should be called after conversation ends
    expect(calledCapIds).toContain("tool.voice.listen_start");
    const lastListenStart = calledCapIds.lastIndexOf("tool.voice.listen_start");
    const lastRecognize = calledCapIds.lastIndexOf("tool.voice.recognize");
    expect(lastListenStart).toBeGreaterThan(lastRecognize);

    voiceLoop.stop();
  });

  it("should handle stop word event and trigger emergency stop", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    const voiceLoop = createVoiceLoop(createMockExecutor());
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

    expect(mockBridge.broadcastStop).toHaveBeenCalledWith("voice");

    voiceLoop.stop();
  });

  it("should exit conversation loop on stop word during ASR", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    // First turn normal, second turn stop word
    const mockExecutor = createMockExecutor([
      { text: "你好" },
      { text: "停", is_stop_word: true },
    ]);

    const dispatchSpy = vi.spyOn(dispatcher, "dispatch").mockResolvedValue("回复");
    const voiceLoop = createVoiceLoop(mockExecutor);

    voiceLoop.start();
    await flushAsync();

    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    // Only first turn dispatched; second turn was stop word
    expect(dispatchSpy).toHaveBeenCalledTimes(1);
    expect(mockBridge.broadcastStop).toHaveBeenCalledWith("voice");

    voiceLoop.stop();
  });

  it("should ignore wake word when not IDLE", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    const voiceLoop = createVoiceLoop(createMockExecutor());
    voiceLoop.start();
    await flushAsync();

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

    expect(dispatchSpy).not.toHaveBeenCalled();

    voiceLoop.stop();
  });

  it("should not TTS in mute mode", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    const mockExecutor = createMockExecutor([{ text: "Hello" }]);
    vi.spyOn(dispatcher, "dispatch").mockResolvedValue("Response");

    stateService.setMode("mute");
    const voiceLoop = createVoiceLoop(mockExecutor);
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

    const synthCalls = mockExecutor.execute.mock.calls.filter(
      (c: any[]) => c[0] === "tool.voice.synthesize"
    );
    expect(synthCalls).toHaveLength(0);

    voiceLoop.stop();
  });

  it("should return to IDLE on immediate ASR timeout (0 turns)", async () => {
    let eventHandler: ((event: ModuleEvent) => void) | null = null;
    mockBridge.onEvent.mockImplementation((handler: any) => {
      eventHandler = handler;
      return () => {};
    });

    // No successful recognitions — immediate timeout
    const mockExecutor = createMockExecutor([]);
    const dispatchSpy = vi.spyOn(dispatcher, "dispatch");
    const voiceLoop = createVoiceLoop(mockExecutor);

    voiceLoop.start();
    await flushAsync();

    await eventHandler!({
      type: "event",
      source: "voice",
      event_type: "voice.wake_word_detected",
      data: {},
      timestamp: Date.now(),
    });
    await flushAsync();

    expect(dispatchSpy).not.toHaveBeenCalled();
    expect(session.current).toBe("IDLE");

    voiceLoop.stop();
  });
});
