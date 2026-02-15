/**
 * IncidentRecorder — automatically captures system incidents as memory entries.
 *
 * Records incidents from:
 * - Module crashes (module_crash)
 * - Tool execution errors (tool_error)
 * - API degradation (api_degradation)
 *
 * Features:
 * - Deduplication: same category:error_code:capability_id within 60s is skipped
 * - 7-day TTL on incident memories (auto-cleaned by CleanupScheduler)
 * - Writes audit log alongside memory creation
 */

import type { MemoryService } from "../memory/memory-service.js";
import type { AuditLogger } from "../audit/audit-logger.js";

export type IncidentCategory = "module_crash" | "tool_error" | "api_degradation";

export interface IncidentInput {
  readonly category: IncidentCategory;
  readonly error_code: string;
  readonly message: string;
  readonly capability_id?: string;
  readonly module_id?: string;
  readonly details?: Record<string, unknown>;
}

const DEDUP_TTL_MS = 60_000; // 60 seconds
const INCIDENT_TTL_DAYS = 7;
/** TTL in seconds — MemoryStore.cleanExpired() treats ttl as seconds. */
const INCIDENT_TTL_S = INCIDENT_TTL_DAYS * 24 * 60 * 60; // 604800

export class IncidentRecorder {
  private readonly dedupCache = new Map<string, number>();

  constructor(
    private readonly memoryService: MemoryService,
    private readonly auditLogger: AuditLogger
  ) {}

  /**
   * Record an incident. Returns the memory ID if created, or null if deduplicated.
   */
  record(input: IncidentInput): string | null {
    const dedupKey = `${input.category}:${input.error_code}:${input.capability_id ?? ""}`;
    const now = Date.now();

    // Dedup check
    const lastSeen = this.dedupCache.get(dedupKey);
    if (lastSeen && now - lastSeen < DEDUP_TTL_MS) {
      return null;
    }
    this.dedupCache.set(dedupKey, now);

    // Clean old dedup entries
    this.cleanDedupCache(now);

    const tags = ["incident", input.category, input.error_code];
    const content: Record<string, unknown> = {
      category: input.category,
      error_code: input.error_code,
      message: input.message,
    };
    if (input.capability_id) content.capability_id = input.capability_id;
    if (input.module_id) content.module_id = input.module_id;
    if (input.details) content.details = input.details;

    const summary = input.capability_id
      ? `${input.category}: ${input.error_code} on ${input.capability_id} — ${input.message}`
      : `${input.category}: ${input.error_code} — ${input.message}`;

    const entry = this.memoryService.create({
      type: "incident",
      content,
      summary,
      source: "system_detected",
      confidence: 1.0,
      privacy_level: "normal",
      tags,
      ttl: INCIDENT_TTL_S,
    });

    this.auditLogger.info("incident", "incident.recorded", {
      incident_id: entry.id,
      category: input.category,
      error_code: input.error_code,
      capability_id: input.capability_id,
    });

    return entry.id;
  }

  private cleanDedupCache(now: number): void {
    for (const [key, timestamp] of this.dedupCache) {
      if (now - timestamp >= DEDUP_TTL_MS) {
        this.dedupCache.delete(key);
      }
    }
  }
}
