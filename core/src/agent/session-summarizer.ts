/**
 * SessionSummarizer — compresses long conversation histories to manage
 * context window size and reduce LLM API costs.
 *
 * Strategy:
 * 1. When message count exceeds threshold, summarize early messages
 * 2. Keep recent N turns intact for conversational coherence
 * 3. Try LLM-based summarization first (richer quality)
 * 4. Fall back to local keyword extraction if LLM unavailable
 */

import { completeSimple, type Model } from "@mariozechner/pi-ai";
import type { AgentMessage } from "@mariozechner/pi-agent-core";
import { extractKeywords } from "../memory/keyword-extractor.js";

export interface SummarizerConfig {
  /** Trigger summarization when message count exceeds this. Default: 20 */
  readonly summarizeAfterMessages: number;
  /** Number of recent messages to keep intact. Default: 10 */
  readonly keepRecentMessages: number;
}

const DEFAULT_CONFIG: SummarizerConfig = {
  summarizeAfterMessages: 20,
  keepRecentMessages: 10,
};

type MessageLike = {
  role?: unknown;
  content?: unknown;
};

/**
 * Extract text content from an AgentMessage regardless of its structure.
 */
function extractText(msg: AgentMessage): string {
  if (!msg || typeof msg !== "object") return "";
  const m = msg as unknown as MessageLike;

  // UserMessage: content is string | (TextContent | ImageContent)[]
  if (typeof m.content === "string") return m.content;

  // AssistantMessage / ToolResultMessage: content is array
  if (Array.isArray(m.content)) {
    return (m.content as Array<Record<string, unknown>>)
      .filter((c) => c.type === "text" && typeof c.text === "string")
      .map((c) => c.text as string)
      .join(" ");
  }

  return "";
}

export class SessionSummarizer {
  private readonly config: SummarizerConfig;

  constructor(
    private readonly model: Model<any>,
    private readonly apiKey?: string,
    config?: Partial<SummarizerConfig>
  ) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Check if conversation needs summarization.
   */
  needsSummarization(messageCount: number): boolean {
    return messageCount > this.config.summarizeAfterMessages;
  }

  /**
   * Summarize older messages and return compressed message list.
   * Recent messages are kept intact for conversational coherence.
   */
  async summarize(messages: AgentMessage[]): Promise<AgentMessage[]> {
    const keepCount = this.config.keepRecentMessages;
    if (messages.length <= keepCount) return messages;

    const toSummarize = messages.slice(0, messages.length - keepCount);
    const toKeep = messages.slice(messages.length - keepCount);

    let summaryText: string;
    try {
      summaryText = await this.llmSummarize(toSummarize);
    } catch {
      summaryText = this.localSummarize(toSummarize);
    }

    const summaryMessage: AgentMessage = {
      role: "user",
      content: `[Previous conversation summary: ${summaryText}]`,
      timestamp: Date.now(),
    };

    return [summaryMessage, ...toKeep];
  }

  /**
   * Use LLM to generate a high-quality summary.
   */
  private async llmSummarize(messages: AgentMessage[]): Promise<string> {
    const conversationText = messages
      .map((m) => {
        const role = (m as unknown as MessageLike).role ?? "unknown";
        const text = extractText(m);
        return text ? `[${role}] ${text}` : "";
      })
      .filter(Boolean)
      .join("\n");

    const result = await completeSimple(
      this.model,
      {
        systemPrompt:
          "You are a conversation summarizer. Summarize the following conversation in 1-2 concise sentences. " +
          "Use the same language as the conversation. Focus on key topics and decisions.",
        messages: [
          {
            role: "user",
            content: `Summarize this conversation:\n\n${conversationText}`,
            timestamp: Date.now(),
          },
        ],
      },
      {
        apiKey: this.apiKey,
      }
    );

    // Extract text from assistant response
    const text = result.content
      .filter((c): c is { type: "text"; text: string } => c.type === "text")
      .map((c) => c.text)
      .join(" ")
      .trim();

    if (!text) throw new Error("Empty summary from LLM");
    return text;
  }

  /**
   * Local keyword-based fallback summary when LLM is unavailable.
   */
  localSummarize(messages: AgentMessage[]): string {
    const allText = messages.map(extractText).filter(Boolean).join(" ");
    const keywords = extractKeywords(allText);
    const topKeywords = keywords.slice(0, 8);
    const turnCount = messages.filter(
      (m) => (m as unknown as MessageLike).role === "user"
    ).length;

    if (topKeywords.length === 0) {
      return `之前有 ${turnCount} 轮对话`;
    }

    return `之前讨论了 ${topKeywords.join("、")}，共 ${turnCount} 轮对话`;
  }
}
