/**
 * Audit types.
 */

export type AuditSeverity = "DEBUG" | "INFO" | "WARN" | "ERROR" | "CRITICAL";

export interface AuditEvent {
  readonly id: string;
  readonly traceId: string;
  readonly eventType: string;
  readonly timestamp: string;
  readonly payload?: Record<string, unknown>;
  readonly severity: AuditSeverity;
  readonly duration_ms?: number;
}
