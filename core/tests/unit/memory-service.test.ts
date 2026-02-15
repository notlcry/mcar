/**
 * MemoryService unit tests.
 *
 * Tests:
 * - CRUD operations
 * - Injection strategy (priority ordering, count limit)
 * - Privacy filtering
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync, unlinkSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryService } from "../../src/memory/memory-service.js";

const TEST_DB_DIR = resolve(__dirname, "../../test-data");
const TEST_DB = resolve(TEST_DB_DIR, "test-memory.db");

describe("MemoryService", () => {
  let service: MemoryService;

  beforeEach(() => {
    if (!existsSync(TEST_DB_DIR)) {
      mkdirSync(TEST_DB_DIR, { recursive: true });
    }
    if (existsSync(TEST_DB)) {
      unlinkSync(TEST_DB);
    }
    service = new MemoryService({ dbPath: TEST_DB, maxInjectionCount: 5 });
  });

  afterEach(() => {
    service.close();
    if (existsSync(TEST_DB)) {
      unlinkSync(TEST_DB);
    }
  });

  // ─── CRUD ─────────────────────────────────────────────────

  it("should create and retrieve a memory", () => {
    const entry = service.create({
      type: "preference",
      content: { key: "volume", value: 0.8 },
      summary: "User prefers 80% volume",
      source: "user_explicit",
    });

    expect(entry.id).toBeTruthy();
    expect(entry.type).toBe("preference");

    const retrieved = service.getById(entry.id);
    expect(retrieved).not.toBeNull();
    expect(retrieved!.summary).toBe("User prefers 80% volume");
  });

  it("should update a memory", () => {
    const entry = service.create({
      type: "fact",
      content: { name: "Bob" },
      summary: "User's name is Bob",
      source: "user_explicit",
    });

    const updated = service.update(entry.id, {
      content: { name: "Alice" },
      summary: "User's name is Alice",
    });

    expect(updated!.summary).toBe("User's name is Alice");
    expect((updated!.content as any).name).toBe("Alice");
  });

  it("should delete a memory", () => {
    const entry = service.create({
      type: "fact",
      content: {},
      summary: "test",
      source: "user_explicit",
    });

    expect(service.delete(entry.id)).toBe(true);
    expect(service.getById(entry.id)).toBeNull();
  });

  it("should search by type", () => {
    service.create({ type: "preference", content: {}, summary: "pref1", source: "user_explicit" });
    service.create({ type: "fact", content: {}, summary: "fact1", source: "user_explicit" });
    service.create({ type: "preference", content: {}, summary: "pref2", source: "user_explicit" });

    const results = service.search({ types: ["preference"] });
    expect(results.length).toBe(2);
  });

  it("should search by keywords", () => {
    service.create({ type: "fact", content: {}, summary: "User likes coffee", source: "user_explicit" });
    service.create({ type: "fact", content: {}, summary: "User likes tea", source: "user_explicit" });

    const results = service.search({ keywords: "coffee" });
    expect(results.length).toBe(1);
    expect(results[0].summary).toContain("coffee");
  });

  // ─── Privacy ──────────────────────────────────────────────

  it("should exclude private memories from search by default", () => {
    service.create({
      type: "fact",
      content: {},
      summary: "public fact",
      source: "user_explicit",
      privacy_level: "normal",
    });
    service.create({
      type: "fact",
      content: {},
      summary: "private fact",
      source: "user_explicit",
      privacy_level: "private",
    });

    const results = service.search();
    expect(results.length).toBe(1);
    expect(results[0].summary).toBe("public fact");
  });

  it("should include private memories when explicitly requested", () => {
    service.create({
      type: "fact",
      content: {},
      summary: "private fact",
      source: "user_explicit",
      privacy_level: "private",
    });

    const results = service.search({ includePrivate: true });
    expect(results.length).toBe(1);
  });

  // ─── Injection strategy ───────────────────────────────────

  it("should inject with priority: rules > preferences > tasks", () => {
    service.create({ type: "task", content: {}, summary: "task 1", source: "system_detected" });
    service.create({ type: "preference", content: {}, summary: "pref 1", source: "user_explicit" });
    service.create({ type: "rule", content: {}, summary: "rule 1", source: "user_explicit" });

    const context = service.getInjectionContext();
    expect(context.length).toBeGreaterThan(0);
    expect(context[0]).toContain("[rule]");
  });

  it("should limit injection to maxInjectionCount", () => {
    for (let i = 0; i < 10; i++) {
      service.create({ type: "preference", content: {}, summary: `pref ${i}`, source: "user_explicit" });
    }

    const context = service.getInjectionContext();
    expect(context.length).toBeLessThanOrEqual(5);
  });

  it("should not inject private memories", () => {
    service.create({
      type: "rule",
      content: {},
      summary: "secret rule",
      source: "user_explicit",
      privacy_level: "private",
    });

    const context = service.getInjectionContext();
    expect(context.length).toBe(0);
  });

  it("should not inject private memories even when mixed with normal ones", () => {
    service.create({
      type: "preference",
      content: {},
      summary: "public pref",
      source: "user_explicit",
      privacy_level: "normal",
    });
    service.create({
      type: "preference",
      content: {},
      summary: "private pref",
      source: "user_explicit",
      privacy_level: "private",
    });

    const context = service.getInjectionContext();
    expect(context.length).toBe(1);
    expect(context[0]).toContain("public pref");
    expect(context.join(" ")).not.toContain("private pref");
  });

  // ─── listSummaries privacy ──────────────────────────────

  it("should exclude private memories from listSummaries", () => {
    service.create({
      type: "fact",
      content: {},
      summary: "visible fact",
      source: "user_explicit",
      privacy_level: "normal",
    });
    service.create({
      type: "fact",
      content: {},
      summary: "secret fact",
      source: "user_explicit",
      privacy_level: "private",
    });

    const summaries = service.listSummaries();
    expect(summaries.length).toBe(1);
    expect(summaries[0].summary).toBe("visible fact");
  });

  // ─── Relevance search ──────────────────────────────────

  it("should return relevant memories by tag matching", () => {
    service.create({
      type: "rule",
      content: {},
      summary: "Speed limit on carpet",
      source: "user_explicit",
      tags: ["motion", "speed", "carpet"],
    });
    service.create({
      type: "preference",
      content: {},
      summary: "User prefers low volume",
      source: "user_explicit",
      tags: ["volume", "audio"],
    });

    const results = service.searchRelevant("motion speed");
    expect(results.length).toBe(1);
    expect(results[0].summary).toContain("carpet");
  });

  it("should not return private memories in relevance search", () => {
    service.create({
      type: "rule",
      content: {},
      summary: "Secret motion rule",
      source: "user_explicit",
      privacy_level: "private",
      tags: ["motion"],
    });

    const results = service.searchRelevant("motion");
    expect(results.length).toBe(0);
  });

  it("should return empty array for unmatched query", () => {
    service.create({
      type: "fact",
      content: {},
      summary: "User likes coffee",
      source: "user_explicit",
      tags: ["coffee"],
    });

    const results = service.searchRelevant("temperature sensor");
    expect(results.length).toBe(0);
  });
});
