/**
 * Memory management tests — delete, clear, export/import.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { MemoryService } from "../../src/memory/memory-service.js";
import { exportMemories, importMemories } from "../../src/memory/memory-export.js";
import type { MemoryCreateInput } from "../../src/memory/types.js";

function createTestMemory(overrides: Partial<MemoryCreateInput> = {}): MemoryCreateInput {
  return {
    type: "preference",
    content: { key: "volume", value: 0.5 },
    summary: "Preferred volume is 50%",
    source: "user_explicit",
    ...overrides,
  };
}

describe("MemoryService management", () => {
  let service: MemoryService;

  beforeEach(() => {
    service = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
  });

  afterEach(() => {
    service.close();
  });

  describe("clearByType", () => {
    it("should clear all memories of a given type", () => {
      service.create(createTestMemory({ type: "preference", summary: "pref 1" }));
      service.create(createTestMemory({ type: "preference", summary: "pref 2" }));
      service.create(createTestMemory({ type: "fact", summary: "a fact" }));

      const deleted = service.clearByType("preference");
      expect(deleted).toBe(2);

      const remaining = service.search({ types: ["preference"], includePrivate: true });
      expect(remaining).toHaveLength(0);

      // Facts should still exist
      const facts = service.search({ types: ["fact"], includePrivate: true });
      expect(facts).toHaveLength(1);
    });

    it("should return 0 when no memories of type exist", () => {
      const deleted = service.clearByType("device");
      expect(deleted).toBe(0);
    });
  });

  describe("searchByKeywords", () => {
    it("should find memories by keyword in summary", () => {
      service.create(createTestMemory({ summary: "I like chocolate" }));
      service.create(createTestMemory({ summary: "My name is Alice" }));
      service.create(createTestMemory({ summary: "Favorite color: blue" }));

      const results = service.searchByKeywords("chocolate");
      expect(results).toHaveLength(1);
      expect(results[0].summary).toBe("I like chocolate");
    });

    it("should find memories by keyword in content", () => {
      service.create(createTestMemory({
        content: { key: "speed_limit", value: 30 },
        summary: "Speed preference",
      }));

      const results = service.searchByKeywords("speed_limit");
      expect(results).toHaveLength(1);
    });

    it("should filter by type", () => {
      service.create(createTestMemory({ type: "preference", summary: "speed pref" }));
      service.create(createTestMemory({ type: "fact", summary: "speed fact" }));

      const results = service.searchByKeywords("speed", ["fact"]);
      expect(results).toHaveLength(1);
      expect(results[0].type).toBe("fact");
    });

    it("should exclude private memories", () => {
      service.create(createTestMemory({
        summary: "secret thing",
        privacy_level: "private",
      }));

      const results = service.searchByKeywords("secret");
      expect(results).toHaveLength(0);
    });
  });

  describe("delete", () => {
    it("should delete a memory by ID", () => {
      const entry = service.create(createTestMemory());
      expect(service.getById(entry.id)).not.toBeNull();

      const deleted = service.delete(entry.id);
      expect(deleted).toBe(true);
      expect(service.getById(entry.id)).toBeNull();
    });

    it("should return false for non-existent ID", () => {
      expect(service.delete("nonexistent")).toBe(false);
    });
  });
});

describe("Memory export/import", () => {
  let source: MemoryService;
  let target: MemoryService;

  beforeEach(() => {
    source = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
    target = new MemoryService({ dbPath: ":memory:", maxInjectionCount: 5 });
  });

  afterEach(() => {
    source.close();
    target.close();
  });

  it("should export all memories", () => {
    source.create(createTestMemory({ summary: "pref 1" }));
    source.create(createTestMemory({ type: "fact", summary: "fact 1" }));

    const exported = exportMemories(source);
    expect(exported.version).toBe("1.0.0");
    expect(exported.count).toBe(2);
    expect(exported.entries).toHaveLength(2);
  });

  it("should export with type filter", () => {
    source.create(createTestMemory({ type: "preference", summary: "pref" }));
    source.create(createTestMemory({ type: "fact", summary: "fact" }));

    const exported = exportMemories(source, { types: ["fact"] });
    expect(exported.count).toBe(1);
    expect(exported.entries[0].type).toBe("fact");
  });

  it("should import memories into target", () => {
    source.create(createTestMemory({ summary: "memory 1" }));
    source.create(createTestMemory({ summary: "memory 2" }));

    const exported = exportMemories(source);
    const result = importMemories(target, exported);

    expect(result.imported).toBe(2);
    expect(result.skipped).toBe(0);
    expect(result.errors).toHaveLength(0);

    const targetEntries = target.search({ includePrivate: true });
    expect(targetEntries).toHaveLength(2);
  });

  it("should skip duplicate entries on import", () => {
    const entry = source.create(createTestMemory({ summary: "original" }));

    const exported = exportMemories(source);

    // Import first time
    const result1 = importMemories(source, exported);
    expect(result1.skipped).toBe(1);
    expect(result1.imported).toBe(0);
  });

  it("should mark imported entries with source 'imported'", () => {
    source.create(createTestMemory({ source: "user_explicit", summary: "test" }));

    const exported = exportMemories(source);
    const result = importMemories(target, exported);

    expect(result.imported).toBe(1);
    const imported = target.search({ includePrivate: true });
    expect(imported[0].source).toBe("imported");
  });
});
