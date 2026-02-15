/**
 * AuditStore — SQLite-backed persistent audit event storage.
 *
 * Provides durable storage for audit events that survives restarts.
 * The in-memory AuditLogger delegates to this store when configured.
 */

import Database from "better-sqlite3";
import type { AuditEvent, AuditSeverity } from "./types.js";

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS audit_events (
    id         TEXT PRIMARY KEY,
    trace_id   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    payload    TEXT,
    severity   TEXT DEFAULT 'INFO'
  );

  CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_events(trace_id);
  CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
  CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
`;

export class AuditStore {
  private db: Database.Database;
  private insertStmt: Database.Statement;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.exec(SCHEMA);

    this.insertStmt = this.db.prepare(
      `INSERT OR IGNORE INTO audit_events (id, trace_id, event_type, timestamp, payload, severity)
       VALUES (?, ?, ?, ?, ?, ?)`
    );
  }

  /**
   * Persist an audit event.
   */
  save(event: AuditEvent): void {
    this.insertStmt.run(
      event.id,
      event.traceId,
      event.eventType,
      event.timestamp,
      event.payload ? JSON.stringify(event.payload) : null,
      event.severity
    );
  }

  /**
   * Get recent events, ordered by timestamp descending.
   */
  getRecent(count = 100): AuditEvent[] {
    const rows = this.db
      .prepare("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?")
      .all(count) as Record<string, unknown>[];
    return rows.map((r) => this.rowToEvent(r));
  }

  /**
   * Get events by trace ID.
   */
  getByTraceId(traceId: string): AuditEvent[] {
    const rows = this.db
      .prepare("SELECT * FROM audit_events WHERE trace_id = ? ORDER BY timestamp ASC")
      .all(traceId) as Record<string, unknown>[];
    return rows.map((r) => this.rowToEvent(r));
  }

  /**
   * Get events by event type.
   */
  getByEventType(eventType: string, limit = 50): AuditEvent[] {
    const rows = this.db
      .prepare("SELECT * FROM audit_events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?")
      .all(eventType, limit) as Record<string, unknown>[];
    return rows.map((r) => this.rowToEvent(r));
  }

  /**
   * Get event count.
   */
  count(): number {
    const row = this.db.prepare("SELECT COUNT(*) as cnt FROM audit_events").get() as { cnt: number };
    return row.cnt;
  }

  /**
   * Export all events as array (for backup).
   */
  exportAll(): AuditEvent[] {
    const rows = this.db
      .prepare("SELECT * FROM audit_events ORDER BY timestamp ASC")
      .all() as Record<string, unknown>[];
    return rows.map((r) => this.rowToEvent(r));
  }

  /**
   * Clean up old events (keep last N days).
   */
  cleanOlderThan(days: number): number {
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    const result = this.db
      .prepare("DELETE FROM audit_events WHERE timestamp < ?")
      .run(cutoff);
    return result.changes;
  }

  close(): void {
    this.db.close();
  }

  private rowToEvent(row: Record<string, unknown>): AuditEvent {
    return {
      id: row.id as string,
      traceId: row.trace_id as string,
      eventType: row.event_type as string,
      timestamp: row.timestamp as string,
      payload: row.payload ? JSON.parse(row.payload as string) : undefined,
      severity: row.severity as AuditSeverity,
    };
  }
}
