/**
 * MemoryService — CRUD + retrieval + injection strategy + privacy filtering.
 *
 * High-level service wrapping MemoryStore with business logic:
 * - Context injection (for ContextBuilder)
 * - Explicit write flow ("remember X")
 * - Privacy filtering
 */

import type {
  MemoryEntry,
  MemoryCreateInput,
  MemorySearchOptions,
  MemoryType,
} from "./types.js";
import { MemoryStore } from "./memory-store.js";
import type { MemoryConfig } from "../config/config.js";
import { extractKeywords, computeRelevanceScore } from "./keyword-extractor.js";

export class MemoryService {
  private readonly store: MemoryStore;
  private readonly maxInjectionCount: number;

  constructor(config: MemoryConfig) {
    this.store = new MemoryStore(config.dbPath);
    this.maxInjectionCount = config.maxInjectionCount;
  }

  // ─── CRUD ─────────────────────────────────────────────────

  create(input: MemoryCreateInput): MemoryEntry {
    return this.store.create(input);
  }

  getById(id: string): MemoryEntry | null {
    return this.store.getById(id);
  }

  update(
    id: string,
    updates: Partial<Pick<MemoryCreateInput, "content" | "summary" | "confidence" | "tags" | "links" | "ttl">>
  ): MemoryEntry | null {
    return this.store.update(id, updates);
  }

  delete(id: string): boolean {
    return this.store.delete(id);
  }

  search(options?: MemorySearchOptions): MemoryEntry[] {
    return this.store.search(options);
  }

  // ─── Context injection ────────────────────────────────────

  /**
   * Build injection context for a given set of capability IDs.
   *
   * Priority order (per Spec.md):
   * 1. Hard rules (rule/device related to capabilities)
   * 2. Preferences (volume, name, etc.)
   * 3. Task context (in-progress tasks/skill_state)
   * 4. Facts/locations (only if strongly related)
   *
   * Returns at most maxInjectionCount entries,
   * private entries are excluded unless explicitly needed.
   */
  getInjectionContext(relatedCapabilityIds?: string[]): string[] {
    const entries: MemoryEntry[] = [];

    // 1. Rules and device constraints
    const rules = this.store.search({
      types: ["rule", "device"],
      includePrivate: false,
      limit: this.maxInjectionCount,
    });
    entries.push(...rules);

    // 2. Preferences
    if (entries.length < this.maxInjectionCount) {
      const prefs = this.store.search({
        types: ["preference"],
        includePrivate: false,
        limit: this.maxInjectionCount - entries.length,
      });
      entries.push(...prefs);
    }

    // 3. Active tasks and skill states
    if (entries.length < this.maxInjectionCount) {
      const tasks = this.store.search({
        types: ["task", "skill_state"],
        includePrivate: false,
        limit: this.maxInjectionCount - entries.length,
      });
      entries.push(...tasks);
    }

    // Deduplicate and limit
    const seen = new Set<string>();
    const result: string[] = [];
    for (const entry of entries) {
      if (seen.has(entry.id)) continue;
      seen.add(entry.id);
      result.push(`[${entry.type}] ${entry.summary}`);
      if (result.length >= this.maxInjectionCount) break;
    }

    return result;
  }

  /**
   * List all memories for user review (privacy-filtered summaries).
   */
  listSummaries(types?: MemoryType[]): Array<{ id: string; type: string; summary: string }> {
    const entries = this.store.search({
      types,
      includePrivate: false,
      limit: 100,
    });
    return entries.map((e) => ({
      id: e.id,
      type: e.type,
      summary: e.privacy_level === "private" ? "[hidden]" : e.summary,
    }));
  }

  /**
   * Delete all memories of a given type.
   */
  clearByType(type: MemoryType): number {
    const entries = this.store.search({ types: [type], includePrivate: true, limit: 10000 });
    let deleted = 0;
    for (const entry of entries) {
      if (this.store.delete(entry.id)) deleted++;
    }
    return deleted;
  }

  /**
   * Search memories by keyword.
   */
  searchByKeywords(keywords: string, types?: MemoryType[]): MemoryEntry[] {
    return this.store.search({
      keywords,
      types,
      includePrivate: false,
      limit: 20,
    });
  }

  // ─── Relevance search ───────────────────────────────────

  /**
   * Search memories by relevance (keyword/tag matching).
   * Extracts keywords from query, scores against entry tags + summary.
   */
  searchRelevant(query: string, types?: MemoryType[]): MemoryEntry[] {
    const queryKeywords = extractKeywords(query);
    if (queryKeywords.length === 0) return [];

    return this.store.searchRelevant(
      queryKeywords,
      (tags, summary) => computeRelevanceScore(queryKeywords, tags, summary),
      {
        types,
        includePrivate: false,
        limit: this.maxInjectionCount,
      }
    );
  }

  // ─── Device constraints ──────────────────────────────────

  /**
   * Get device memory entries that define constraints
   * (e.g., hardware limits, calibration data, fault history).
   */
  getDeviceConstraints(): MemoryEntry[] {
    return this.store.search({
      types: ["device"],
      includePrivate: true,
      limit: 20,
    });
  }

  /**
   * Clean up expired memories.
   */
  cleanExpired(): number {
    return this.store.cleanExpired();
  }

  close(): void {
    this.store.close();
  }
}
