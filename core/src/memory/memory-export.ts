/**
 * MemoryExport — export/import memory entries for backup and migration.
 *
 * Export format: JSON array of memory entries.
 */

import type { MemoryService } from "./memory-service.js";
import type { MemoryEntry, MemoryCreateInput, MemoryType } from "./types.js";

export interface ExportOptions {
  readonly types?: readonly MemoryType[];
  readonly includePrivate?: boolean;
}

export interface ExportResult {
  readonly version: string;
  readonly exported_at: string;
  readonly count: number;
  readonly entries: readonly MemoryEntry[];
}

export interface ImportResult {
  readonly imported: number;
  readonly skipped: number;
  readonly errors: string[];
}

const EXPORT_VERSION = "1.0.0";

/**
 * Export memories to a serializable structure.
 */
export function exportMemories(
  memoryService: MemoryService,
  options: ExportOptions = {}
): ExportResult {
  const entries = memoryService.search({
    types: options.types as MemoryType[] | undefined,
    includePrivate: options.includePrivate ?? true,
    limit: 10000,
  });

  return {
    version: EXPORT_VERSION,
    exported_at: new Date().toISOString(),
    count: entries.length,
    entries,
  };
}

/**
 * Import memories from an exported structure.
 * Skips entries that already exist (by ID).
 */
export function importMemories(
  memoryService: MemoryService,
  data: ExportResult
): ImportResult {
  let imported = 0;
  let skipped = 0;
  const errors: string[] = [];

  for (const entry of data.entries) {
    // Check if already exists
    const existing = memoryService.getById(entry.id);
    if (existing) {
      skipped++;
      continue;
    }

    try {
      const input: MemoryCreateInput = {
        type: entry.type,
        content: entry.content,
        summary: entry.summary,
        source: "imported",
        confidence: entry.confidence,
        privacy_level: entry.privacy_level,
        tags: [...entry.tags],
        links: { ...entry.links },
        ttl: entry.ttl,
      };
      memoryService.create(input);
      imported++;
    } catch (err) {
      errors.push(`Failed to import entry ${entry.id}: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return { imported, skipped, errors };
}
