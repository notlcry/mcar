/**
 * AuditLogger — structured event logging for traceability.
 */

import { v4 as uuid } from "uuid";
import type { AuditEvent, AuditSeverity } from "./types.js";
import type { AuditStore } from "./audit-store.js";

type AuditListener = (event: AuditEvent) => void;

export class AuditLogger {
  private listeners: AuditListener[] = [];
  private buffer: AuditEvent[] = [];
  private readonly maxBuffer: number;
  private store: AuditStore | null = null;

  constructor(options?: { maxBuffer?: number }) {
    this.maxBuffer = options?.maxBuffer ?? 1000;
  }

  /**
   * Attach a persistent store for audit events.
   */
  setStore(store: AuditStore): void {
    this.store = store;
  }

  log(
    traceId: string,
    eventType: string,
    payload?: Record<string, unknown>,
    severity: AuditSeverity = "INFO",
    duration_ms?: number
  ): AuditEvent {
    const event: AuditEvent = {
      id: uuid(),
      traceId,
      eventType,
      timestamp: new Date().toISOString(),
      payload,
      severity,
      duration_ms,
    };

    this.buffer.push(event);
    if (this.buffer.length > this.maxBuffer) {
      this.buffer.shift();
    }

    // Persist to SQLite if store attached
    if (this.store) {
      try { this.store.save(event); } catch { /* swallow persistence errors */ }
    }

    for (const listener of this.listeners) {
      listener(event);
    }

    return event;
  }

  info(traceId: string, eventType: string, payload?: Record<string, unknown>): AuditEvent {
    return this.log(traceId, eventType, payload, "INFO");
  }

  warn(traceId: string, eventType: string, payload?: Record<string, unknown>): AuditEvent {
    return this.log(traceId, eventType, payload, "WARN");
  }

  error(traceId: string, eventType: string, payload?: Record<string, unknown>): AuditEvent {
    return this.log(traceId, eventType, payload, "ERROR");
  }

  getRecent(count = 50): AuditEvent[] {
    return this.buffer.slice(-count);
  }

  getByTraceId(traceId: string): AuditEvent[] {
    return this.buffer.filter((e) => e.traceId === traceId);
  }

  /**
   * Execute an async function and log its duration upon completion.
   */
  async timed<T>(
    traceId: string,
    eventType: string,
    fn: () => Promise<T>,
    payload?: Record<string, unknown>
  ): Promise<T> {
    const start = Date.now();
    try {
      const result = await fn();
      const duration_ms = Date.now() - start;
      this.log(traceId, eventType, { ...payload, success: true }, "INFO", duration_ms);
      return result;
    } catch (err) {
      const duration_ms = Date.now() - start;
      const message = err instanceof Error ? err.message : String(err);
      this.log(traceId, eventType, { ...payload, success: false, error: message }, "ERROR", duration_ms);
      throw err;
    }
  }

  onEvent(listener: AuditListener): () => void {
    this.listeners.push(listener);
    return () => {
      const idx = this.listeners.indexOf(listener);
      if (idx >= 0) this.listeners.splice(idx, 1);
    };
  }
}
