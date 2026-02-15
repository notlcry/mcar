/**
 * KeywordExtractor unit tests.
 */

import { describe, it, expect } from "vitest";
import { extractKeywords, computeRelevanceScore } from "../../src/memory/keyword-extractor.js";

describe("extractKeywords", () => {
  it("should extract English words and filter stop words", () => {
    const keywords = extractKeywords("The robot should move forward quickly");
    expect(keywords).toContain("robot");
    expect(keywords).toContain("move");
    expect(keywords).toContain("forward");
    expect(keywords).toContain("quickly");
    expect(keywords).not.toContain("the");
    expect(keywords).not.toContain("should");
  });

  it("should extract Chinese characters and bigrams", () => {
    const keywords = extractKeywords("机器人前进速度");
    expect(keywords).toContain("机器");
    expect(keywords).toContain("器人");
    expect(keywords).toContain("前进");
    expect(keywords).toContain("速度");
  });

  it("should filter Chinese stop words", () => {
    const keywords = extractKeywords("我的机器人");
    expect(keywords).not.toContain("我");
    expect(keywords).not.toContain("的");
  });

  it("should handle mixed Chinese and English text", () => {
    const keywords = extractKeywords("motion forward 前进");
    expect(keywords).toContain("motion");
    expect(keywords).toContain("forward");
    expect(keywords).toContain("前进");
  });

  it("should return empty array for empty text", () => {
    expect(extractKeywords("")).toEqual([]);
    expect(extractKeywords("   ")).toEqual([]);
  });

  it("should lowercase English words", () => {
    const keywords = extractKeywords("Robot FORWARD Speed");
    expect(keywords).toContain("robot");
    expect(keywords).toContain("forward");
    expect(keywords).toContain("speed");
  });

  it("should deduplicate keywords", () => {
    const keywords = extractKeywords("robot robot robot");
    const robotCount = keywords.filter((k) => k === "robot").length;
    expect(robotCount).toBe(1);
  });
});

describe("computeRelevanceScore", () => {
  it("should score higher for tag matches", () => {
    const score = computeRelevanceScore(
      ["motion", "speed"],
      ["motion", "forward"],
      "Move forward at speed 50"
    );
    // "motion" matches tag (3) + summary (1) = 4
    // "speed" matches summary (1) = 1
    // total = 5
    expect(score).toBeGreaterThanOrEqual(4);
  });

  it("should return 0 for no matches", () => {
    const score = computeRelevanceScore(
      ["temperature", "sensor"],
      ["motion"],
      "Move forward"
    );
    expect(score).toBe(0);
  });

  it("should return 0 for empty query keywords", () => {
    const score = computeRelevanceScore(
      [],
      ["motion"],
      "Move forward"
    );
    expect(score).toBe(0);
  });
});
