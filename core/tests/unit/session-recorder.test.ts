/**
 * Session recorder tests.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { SessionRecorder } from "../../src/audit/session-recorder.js";
import { AuditStore } from "../../src/audit/audit-store.js";
import type { AuditEvent } from "../../src/audit/types.js";

function makeEvent(overrides: Partial<AuditEvent> = {}): AuditEvent {
  return {
    id: `evt-${Math.random().toString(36).slice(2, 8)}`,
    traceId: "trace1",
    eventType: "test.event",
    timestamp: new Date().toISOString(),
    severity: "INFO",
    ...overrides,
  };
}

describe("SessionRecorder (in-memory)", () => {
  let recorder: SessionRecorder;

  beforeEach(() => {
    recorder = new SessionRecorder();
  });

  it("should start and end a session", () => {
    const sessionId = recorder.startSession("Hello");
    expect(sessionId).toBeTruthy();
    expect(recorder.getActiveSessionId()).toBe(sessionId);

    const endedId = recorder.endSession();
    expect(endedId).toBe(sessionId);
    expect(recorder.getActiveSessionId()).toBeNull();
  });

  it("should track event count", () => {
    const sessionId = recorder.startSession("test");

    recorder.recordEvent(makeEvent());
    recorder.recordEvent(makeEvent());
    recorder.recordEvent(makeEvent());

    const summary = recorder.getSession(sessionId);
    expect(summary?.eventCount).toBe(3);
    expect(summary?.userInput).toBe("test");
  });

  it("should auto-end previous session on new start", () => {
    const id1 = recorder.startSession("first");
    recorder.recordEvent(makeEvent());

    const id2 = recorder.startSession("second");
    expect(id2).not.toBe(id1);

    const first = recorder.getSession(id1);
    expect(first?.endedAt).toBeTruthy();
    expect(recorder.getActiveSessionId()).toBe(id2);
  });

  it("should list sessions in reverse chronological order", () => {
    const id1 = recorder.startSession("first");
    recorder.endSession();

    const id2 = recorder.startSession("second");
    recorder.endSession();

    const sessions = recorder.listSessions();
    expect(sessions).toHaveLength(2);
    expect(sessions[0].sessionId).toBe(id2);
    expect(sessions[1].sessionId).toBe(id1);
  });

  it("should limit listed sessions", () => {
    for (let i = 0; i < 5; i++) {
      recorder.startSession(`session ${i}`);
      recorder.endSession();
    }
    const sessions = recorder.listSessions(3);
    expect(sessions).toHaveLength(3);
  });

  it("should ignore events when no active session", () => {
    recorder.recordEvent(makeEvent());
    expect(recorder.count()).toBe(0);
  });

  it("should return null for endSession when no active session", () => {
    expect(recorder.endSession()).toBeNull();
  });

  it("should return null for unknown session replay", () => {
    expect(recorder.getReplay("nonexistent")).toBeNull();
  });

  it("should count sessions", () => {
    recorder.startSession("a");
    recorder.endSession();
    recorder.startSession("b");
    recorder.endSession();
    expect(recorder.count()).toBe(2);
  });
});

describe("SessionRecorder (with AuditStore)", () => {
  let store: AuditStore;
  let recorder: SessionRecorder;

  beforeEach(() => {
    store = new AuditStore(":memory:");
    recorder = new SessionRecorder(store);
  });

  afterEach(() => {
    store.close();
  });

  it("should replay events from store by session traceId", () => {
    const sessionId = recorder.startSession("replay test");

    // Save events directly to store with sessionId as traceId
    store.save({
      id: "evt1",
      traceId: sessionId,
      eventType: "dispatch.start",
      timestamp: new Date().toISOString(),
      severity: "INFO",
      payload: { text: "hello" },
    });
    store.save({
      id: "evt2",
      traceId: sessionId,
      eventType: "dispatch.complete",
      timestamp: new Date().toISOString(),
      severity: "INFO",
    });

    recorder.recordEvent(makeEvent({ id: "evt1" }));
    recorder.recordEvent(makeEvent({ id: "evt2" }));
    recorder.endSession();

    const replay = recorder.getReplay(sessionId);
    expect(replay).toBeTruthy();
    expect(replay!.events).toHaveLength(2);
    expect(replay!.events[0].eventType).toBe("dispatch.start");
    expect(replay!.startedAt).toBeTruthy();
    expect(replay!.endedAt).toBeTruthy();
  });

  it("should return empty events for session with no store events", () => {
    const sessionId = recorder.startSession("empty");
    recorder.endSession();

    const replay = recorder.getReplay(sessionId);
    expect(replay).toBeTruthy();
    expect(replay!.events).toHaveLength(0);
  });
});
