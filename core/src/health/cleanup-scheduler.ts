/**
 * CleanupScheduler — periodic cleanup of expired memories and old audit logs.
 *
 * Runs on a configurable interval (default: 1 hour) and performs:
 * 1. Memory TTL expiration (via MemoryService.cleanExpired())
 * 2. Audit log rotation (via AuditStore.cleanOlderThan())
 */

import type { MemoryService } from "../memory/memory-service.js";
import type { AuditStore } from "../audit/audit-store.js";
import type { AuditLogger } from "../audit/audit-logger.js";

export interface CleanupConfig {
  /** Interval between cleanup runs in milliseconds. Default: 1 hour */
  readonly intervalMs?: number;
  /** Number of days to retain audit events. Default: 30 */
  readonly auditRetentionDays?: number;
}

export class CleanupScheduler {
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly intervalMs: number;
  private readonly auditRetentionDays: number;

  constructor(
    private readonly memoryService: MemoryService,
    private readonly auditStore: AuditStore | null,
    private readonly auditLogger: AuditLogger,
    config?: CleanupConfig
  ) {
    this.intervalMs = config?.intervalMs ?? 3_600_000; // 1 hour
    this.auditRetentionDays = config?.auditRetentionDays ?? 30;
  }

  /**
   * Start the periodic cleanup timer.
   */
  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.runCleanup(), this.intervalMs);
  }

  /**
   * Stop the cleanup timer.
   */
  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /**
   * Execute a single cleanup run (can be called manually).
   */
  runCleanup(): { memoriesCleaned: number; auditCleaned: number } {
    let memoriesCleaned = 0;
    let auditCleaned = 0;

    try {
      memoriesCleaned = this.memoryService.cleanExpired();
    } catch {
      // Swallow — don't let cleanup failure affect system
    }

    try {
      if (this.auditStore) {
        auditCleaned = this.auditStore.cleanOlderThan(this.auditRetentionDays);
      }
    } catch {
      // Swallow
    }

    if (memoriesCleaned > 0 || auditCleaned > 0) {
      this.auditLogger.info("system", "cleanup.complete", {
        memoriesCleaned,
        auditCleaned,
      });
    }

    return { memoriesCleaned, auditCleaned };
  }

  /**
   * Check if the scheduler is running.
   */
  isRunning(): boolean {
    return this.timer !== null;
  }
}
