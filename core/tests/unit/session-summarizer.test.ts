import { describe, it, expect, vi } from "vitest";
import { SessionSummarizer } from "../../src/agent/session-summarizer.js";
import type { AgentMessage } from "@mariozechner/pi-agent-core";

// Mock completeSimple at module level
vi.mock("@mariozechner/pi-ai", () => ({
  completeSimple: vi.fn(),
}));

import { completeSimple } from "@mariozechner/pi-ai";
const mockComplete = vi.mocked(completeSimple);

function makeUserMsg(text: string): AgentMessage {
  return { role: "user", content: text, timestamp: Date.now() } as AgentMessage;
}

function makeAssistantMsg(text: string): AgentMessage {
  return {
    role: "assistant",
    content: [{ type: "text", text }],
    timestamp: Date.now(),
    api: "google-generative-ai",
    provider: "google-generative-ai",
    model: "gemini-2.5-flash",
    usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
    stopReason: "stop",
  } as unknown as AgentMessage;
}

function makeMessages(count: number): AgentMessage[] {
  const msgs: AgentMessage[] = [];
  for (let i = 0; i < count; i++) {
    msgs.push(
      i % 2 === 0
        ? makeUserMsg(`User message ${i}`)
        : makeAssistantMsg(`Assistant reply ${i}`)
    );
  }
  return msgs;
}

const mockModel = {} as any;

describe("SessionSummarizer", () => {
  describe("needsSummarization", () => {
    it("should return false when below threshold", () => {
      const summarizer = new SessionSummarizer(mockModel, undefined, {
        summarizeAfterMessages: 20,
      });
      expect(summarizer.needsSummarization(15)).toBe(false);
    });

    it("should return false at exactly the threshold", () => {
      const summarizer = new SessionSummarizer(mockModel, undefined, {
        summarizeAfterMessages: 20,
      });
      expect(summarizer.needsSummarization(20)).toBe(false);
    });

    it("should return true above threshold", () => {
      const summarizer = new SessionSummarizer(mockModel, undefined, {
        summarizeAfterMessages: 20,
      });
      expect(summarizer.needsSummarization(25)).toBe(true);
    });
  });

  describe("summarize with LLM", () => {
    it("should keep recent messages and summarize older ones", async () => {
      mockComplete.mockResolvedValueOnce({
        role: "assistant",
        content: [{ type: "text", text: "User asked about weather and pets." }],
        timestamp: Date.now(),
        api: "google-generative-ai",
        provider: "google-generative-ai",
        model: "gemini-2.5-flash",
        usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        stopReason: "stop",
      } as any);

      const summarizer = new SessionSummarizer(mockModel, "test-key", {
        summarizeAfterMessages: 10,
        keepRecentMessages: 4,
      });

      const messages = makeMessages(12);
      const result = await summarizer.summarize(messages);

      // 1 summary + 4 recent = 5 messages
      expect(result).toHaveLength(5);
      // First message is the summary
      expect((result[0] as any).content).toContain("Previous conversation summary");
      expect((result[0] as any).content).toContain("weather and pets");
      // Last 4 are kept intact
      expect(result.slice(1)).toEqual(messages.slice(-4));
    });

    it("should reduce message count after summarization", async () => {
      mockComplete.mockResolvedValueOnce({
        role: "assistant",
        content: [{ type: "text", text: "Summary of the chat." }],
        timestamp: Date.now(),
        api: "google-generative-ai",
        provider: "google-generative-ai",
        model: "gemini-2.5-flash",
        usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        stopReason: "stop",
      } as any);

      const summarizer = new SessionSummarizer(mockModel, "test-key", {
        summarizeAfterMessages: 10,
        keepRecentMessages: 6,
      });

      const messages = makeMessages(20);
      const result = await summarizer.summarize(messages);

      // 1 summary + 6 recent = 7 (much less than 20)
      expect(result).toHaveLength(7);
      expect(result.length).toBeLessThan(messages.length);
    });
  });

  describe("summarize with local fallback", () => {
    it("should use keyword extraction when LLM fails", async () => {
      mockComplete.mockRejectedValueOnce(new Error("API unavailable"));

      const summarizer = new SessionSummarizer(mockModel, undefined, {
        summarizeAfterMessages: 5,
        keepRecentMessages: 2,
      });

      const messages = [
        makeUserMsg("Tell me about robot navigation"),
        makeAssistantMsg("Robot navigation uses sensors and motors."),
        makeUserMsg("What about obstacle avoidance?"),
        makeAssistantMsg("Ultrasonic sensors detect obstacles ahead."),
        makeUserMsg("How fast can it move?"),
        makeAssistantMsg("Speed depends on mode: normal 100%, safety 50%."),
      ];

      const result = await summarizer.summarize(messages);

      // 1 summary + 2 recent = 3 messages
      expect(result).toHaveLength(3);
      // Summary uses keyword-based format
      const summaryContent = (result[0] as any).content as string;
      expect(summaryContent).toContain("Previous conversation summary");
      // Last 2 messages kept intact
      expect(result.slice(1)).toEqual(messages.slice(-2));
    });
  });

  describe("localSummarize", () => {
    it("should extract keywords and count turns", () => {
      const summarizer = new SessionSummarizer(mockModel);

      const messages = [
        makeUserMsg("机器人导航怎么做"),
        makeAssistantMsg("需要传感器和电机配合"),
        makeUserMsg("超声波传感器好用吗"),
      ];

      const result = summarizer.localSummarize(messages);

      expect(result).toContain("之前讨论了");
      expect(result).toContain("共 2 轮对话"); // 2 user messages
    });

    it("should handle empty messages", () => {
      const summarizer = new SessionSummarizer(mockModel);
      const result = summarizer.localSummarize([]);
      expect(result).toContain("之前有 0 轮对话");
    });
  });

  describe("edge cases", () => {
    it("should return messages unchanged when fewer than keepRecentMessages", async () => {
      const summarizer = new SessionSummarizer(mockModel, undefined, {
        summarizeAfterMessages: 5,
        keepRecentMessages: 10,
      });

      const messages = makeMessages(6);
      const result = await summarizer.summarize(messages);

      // 6 messages <= keepRecentMessages(10), so return unchanged
      expect(result).toEqual(messages);
    });

    it("should use default config when none provided", () => {
      const summarizer = new SessionSummarizer(mockModel);
      // Default: summarizeAfterMessages = 20
      expect(summarizer.needsSummarization(19)).toBe(false);
      expect(summarizer.needsSummarization(21)).toBe(true);
    });
  });
});
