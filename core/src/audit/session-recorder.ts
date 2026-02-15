/**
 * SessionRecorder — captures per-session event streams for replay & debugging.
 *
 * Each "session" starts when the user sends a message and ends
 * when the agent responds. The recorder stores events to AuditStore
 * grouped by a session ID, and provides retrieval/export APIs.
 */

import { v4 as uuid } from "uuid";
import type { AuditStore } from "./audit-store.js";
import type { AuditEvent } from "./types.js";

export interface SessionSummary {
  readonly sessionId: string;
  readonly startedAt: string;
  readonly endedAt: string | null;
  readonly eventCount: number;
  readonly userInput?: string;
}

export interface SessionReplay {
  readonly sessionId: string;
  readonly events: readonly AuditEvent[];
  readonly startedAt: string;
  readonly endedAt: string | null;
}

interface ActiveSession {
  sessionId: string;
  startedAt: string;
  userInput?: string;
  eventIds: string[];
}

export class SessionRecorder {
  private activeSession: ActiveSession | null = null;
  private sessions = new Map<string, SessionSummary>();
  private sessionOrder: string[] = [];

  constructor(private readonly store?: AuditStore) {}

  /**
   * Begin recording a new session. Returns session ID.
   */
  startSession(userInput?: string): string {
    // End previous session if still active
    if (this.activeSession) {
      this.endSession();
    }

    const sessionId = uuid();
    const now = new Date().toISOString();

    this.activeSession = {
      sessionId,
      startedAt: now,
      userInput,
      eventIds: [],
    };

    this.sessions.set(sessionId, {
      sessionId,
      startedAt: now,
      endedAt: null,
      eventCount: 0,
      userInput,
    });
    this.sessionOrder.push(sessionId);

    return sessionId;
  }

  /**
   * Record an audit event under the current session.
   */
  recordEvent(event: AuditEvent): void {
    if (!this.activeSession) return;
    this.activeSession.eventIds.push(event.id);

    const summary = this.sessions.get(this.activeSession.sessionId);
    if (summary) {
      this.sessions.set(this.activeSession.sessionId, {
        ...summary,
        eventCount: summary.eventCount + 1,
      });
    }
  }

  /**
   * End the current session.
   */
  endSession(): string | null {
    if (!this.activeSession) return null;

    const sessionId = this.activeSession.sessionId;
    const now = new Date().toISOString();

    const summary = this.sessions.get(sessionId);
    if (summary) {
      this.sessions.set(sessionId, {
        ...summary,
        endedAt: now,
      });
    }

    this.activeSession = null;
    return sessionId;
  }

  /**
   * Get current active session ID.
   */
  getActiveSessionId(): string | null {
    return this.activeSession?.sessionId ?? null;
  }

  /**
   * List recent sessions.
   */
  listSessions(limit = 20): SessionSummary[] {
    const result: SessionSummary[] = [];
    for (let i = this.sessionOrder.length - 1; i >= 0 && result.length < limit; i--) {
      const summary = this.sessions.get(this.sessionOrder[i]);
      if (summary) result.push(summary);
    }
    return result;
  }

  /**
   * Get session summary by ID.
   */
  getSession(sessionId: string): SessionSummary | undefined {
    return this.sessions.get(sessionId);
  }

  /**
   * Get full replay data for a session (events from audit store by traceId).
   */
  getReplay(sessionId: string): SessionReplay | null {
    const summary = this.sessions.get(sessionId);
    if (!summary) return null;

    let events: AuditEvent[] = [];
    if (this.store) {
      events = this.store.getByTraceId(sessionId);
    }

    return {
      sessionId,
      events,
      startedAt: summary.startedAt,
      endedAt: summary.endedAt,
    };
  }

  /**
   * Get total session count.
   */
  count(): number {
    return this.sessions.size;
  }
}
