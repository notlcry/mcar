/**
 * MemoryStore — SQLite backend for persistent memory.
 */

import Database from "better-sqlite3";
import { v4 as uuid } from "uuid";
import type {
  MemoryEntry,
  MemoryCreateInput,
  MemorySearchOptions,
} from "./types.js";

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS memories (
    id            TEXT PRIMARY KEY,
    type          TEXT NOT NULL,
    content       TEXT NOT NULL,
    summary       TEXT NOT NULL,
    source        TEXT NOT NULL,
    confidence    REAL DEFAULT 0.5,
    privacy_level TEXT DEFAULT 'normal',
    tags          TEXT DEFAULT '[]',
    links         TEXT DEFAULT '{}',
    ttl           INTEGER,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
  CREATE INDEX IF NOT EXISTS idx_memories_privacy ON memories(privacy_level);

  CREATE TABLE IF NOT EXISTS audit_events (
    id         TEXT PRIMARY KEY,
    trace_id   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    payload    TEXT,
    severity   TEXT DEFAULT 'INFO'
  );

  CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_events(trace_id);
`;

export class MemoryStore {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.db.exec(SCHEMA);
  }

  create(input: MemoryCreateInput): MemoryEntry {
    const id = uuid();
    const now = new Date().toISOString();
    const entry: MemoryEntry = {
      id,
      type: input.type,
      content: input.content,
      summary: input.summary,
      source: input.source,
      confidence: input.confidence ?? 0.5,
      privacy_level: input.privacy_level ?? "normal",
      tags: input.tags ?? [],
      links: input.links ?? {},
      ttl: input.ttl,
      created_at: now,
      updated_at: now,
    };

    this.db
      .prepare(
        `INSERT INTO memories (id, type, content, summary, source, confidence,
         privacy_level, tags, links, ttl, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        entry.id,
        entry.type,
        JSON.stringify(entry.content),
        entry.summary,
        entry.source,
        entry.confidence,
        entry.privacy_level,
        JSON.stringify(entry.tags),
        JSON.stringify(entry.links),
        entry.ttl ?? null,
        entry.created_at,
        entry.updated_at
      );

    return entry;
  }

  getById(id: string): MemoryEntry | null {
    const row = this.db.prepare("SELECT * FROM memories WHERE id = ?").get(id) as
      | Record<string, unknown>
      | undefined;
    if (!row) return null;
    return this.rowToEntry(row);
  }

  update(
    id: string,
    updates: Partial<Pick<MemoryCreateInput, "content" | "summary" | "confidence" | "tags" | "links" | "ttl">>
  ): MemoryEntry | null {
    const existing = this.getById(id);
    if (!existing) return null;

    const now = new Date().toISOString();
    const fields: string[] = ["updated_at = ?"];
    const values: unknown[] = [now];

    if (updates.content !== undefined) {
      fields.push("content = ?");
      values.push(JSON.stringify(updates.content));
    }
    if (updates.summary !== undefined) {
      fields.push("summary = ?");
      values.push(updates.summary);
    }
    if (updates.confidence !== undefined) {
      fields.push("confidence = ?");
      values.push(updates.confidence);
    }
    if (updates.tags !== undefined) {
      fields.push("tags = ?");
      values.push(JSON.stringify(updates.tags));
    }
    if (updates.links !== undefined) {
      fields.push("links = ?");
      values.push(JSON.stringify(updates.links));
    }
    if (updates.ttl !== undefined) {
      fields.push("ttl = ?");
      values.push(updates.ttl);
    }

    values.push(id);
    this.db.prepare(`UPDATE memories SET ${fields.join(", ")} WHERE id = ?`).run(...values);

    return this.getById(id);
  }

  delete(id: string): boolean {
    const result = this.db.prepare("DELETE FROM memories WHERE id = ?").run(id);
    return result.changes > 0;
  }

  search(options: MemorySearchOptions = {}): MemoryEntry[] {
    const conditions: string[] = [];
    const params: unknown[] = [];

    if (options.types && options.types.length > 0) {
      const placeholders = options.types.map(() => "?").join(",");
      conditions.push(`type IN (${placeholders})`);
      params.push(...options.types);
    }

    if (!options.includePrivate) {
      conditions.push("privacy_level != 'private'");
    }

    if (options.keywords) {
      conditions.push("(summary LIKE ? OR content LIKE ?)");
      const keyword = `%${options.keywords}%`;
      params.push(keyword, keyword);
    }

    if (options.tags && options.tags.length > 0) {
      for (const tag of options.tags) {
        conditions.push("tags LIKE ?");
        params.push(`%"${tag}"%`);
      }
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
    const limit = options.limit ?? 50;

    const rows = this.db
      .prepare(`SELECT * FROM memories ${where} ORDER BY updated_at DESC LIMIT ?`)
      .all(...params, limit) as Record<string, unknown>[];

    return rows.map((row) => this.rowToEntry(row));
  }

  /**
   * Clean up expired entries based on TTL.
   */
  cleanExpired(): number {
    const result = this.db
      .prepare(
        `DELETE FROM memories WHERE ttl IS NOT NULL
         AND datetime(created_at, '+' || ttl || ' seconds') < datetime('now')`
      )
      .run();
    return result.changes;
  }

  /**
   * Search with relevance scoring based on keyword/tag overlap.
   * Returns entries sorted by relevance score (descending).
   */
  searchRelevant(
    queryKeywords: string[],
    scoreFn: (tags: string[], summary: string) => number,
    options: MemorySearchOptions = {}
  ): MemoryEntry[] {
    // Get candidates with standard filtering
    const candidates = this.search({ ...options, limit: 200 });

    // Score and sort
    const scored = candidates.map((entry) => ({
      entry,
      score: scoreFn(entry.tags, entry.summary),
    }));

    scored.sort((a, b) => b.score - a.score);

    const limit = options.limit ?? 50;
    return scored
      .filter((s) => s.score > 0)
      .slice(0, limit)
      .map((s) => s.entry);
  }

  close(): void {
    this.db.close();
  }

  private rowToEntry(row: Record<string, unknown>): MemoryEntry {
    return {
      id: row.id as string,
      type: row.type as MemoryEntry["type"],
      content: JSON.parse(row.content as string),
      summary: row.summary as string,
      source: row.source as MemoryEntry["source"],
      confidence: row.confidence as number,
      privacy_level: row.privacy_level as MemoryEntry["privacy_level"],
      tags: JSON.parse(row.tags as string),
      links: JSON.parse(row.links as string),
      ttl: row.ttl as number | undefined,
      created_at: row.created_at as string,
      updated_at: row.updated_at as string,
    };
  }
}
