/**
 * AgentRuntime — wraps pi-agent-core Agent with mcar system integration.
 *
 * Responsibilities:
 * - Creates and configures the Agent with Gemini model
 * - Manages tool registration (from CapabilityRegistry)
 * - Provides prompt/abort/subscribe interface to Orchestrator
 * - Updates system prompt on each call via PromptBuilder
 */

import { Agent, type AgentEvent, type AgentTool } from "@mariozechner/pi-agent-core";
import { getModel, type Model } from "@mariozechner/pi-ai";
import type { LlmConfig } from "../config/config.js";
import type { PromptBuilder } from "./prompt-builder.js";
import type { CapabilityRegistry } from "../capability/registry.js";
import type { CapabilityExecutor } from "../capability/executor.js";
import type { PolicyEngine } from "../safety/policy-engine.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { MemoryService } from "../memory/memory-service.js";
import type { IncidentRecorder } from "../observability/incident-recorder.js";
import { SessionSummarizer, type SummarizerConfig } from "./session-summarizer.js";
import { buildToolsFromRegistry } from "./tool-adapter.js";

export class AgentRuntime {
  private agent: Agent;
  private readonly model: Model<any>;
  private readonly summarizer: SessionSummarizer;

  constructor(
    private readonly llmConfig: LlmConfig,
    private readonly promptBuilder: PromptBuilder,
    private readonly registry: CapabilityRegistry,
    private readonly executor: CapabilityExecutor,
    private readonly policyEngine: PolicyEngine,
    private readonly auditLogger: AuditLogger,
    private readonly memoryService?: MemoryService,
    private readonly incidentRecorder?: IncidentRecorder,
    summarizerConfig?: Partial<SummarizerConfig>
  ) {
    this.model = getModel(
      llmConfig.provider as any,
      llmConfig.model as any
    );

    this.summarizer = new SessionSummarizer(
      this.model,
      llmConfig.apiKey,
      summarizerConfig
    );

    this.agent = new Agent({
      initialState: {
        systemPrompt: this.promptBuilder.build(),
        model: this.model,
        thinkingLevel: "low",
        tools: [],
      },
      getApiKey: llmConfig.apiKey
        ? async () => llmConfig.apiKey
        : undefined,
    });
  }

  /**
   * Send a user prompt and wait for completion.
   * Refreshes system prompt and tools before each call.
   */
  async prompt(text: string): Promise<void> {
    // Refresh system prompt with latest state/memory/capabilities
    this.agent.setSystemPrompt(this.promptBuilder.build());

    // Refresh tools from registry
    const tools = this.buildTools();
    this.agent.setTools(tools);

    // Compress long conversations to manage context window
    const msgs = this.agent.state.messages;
    if (this.summarizer.needsSummarization(msgs.length)) {
      const compressed = await this.summarizer.summarize(msgs);
      this.agent.replaceMessages(compressed);
    }

    await this.agent.prompt(text);
  }

  /**
   * Abort current processing.
   */
  abort(): void {
    this.agent.abort();
  }

  /**
   * Wait for idle state.
   */
  async waitForIdle(): Promise<void> {
    await this.agent.waitForIdle();
  }

  /**
   * Subscribe to agent events (for UI streaming).
   */
  subscribe(handler: (event: AgentEvent) => void): () => void {
    return this.agent.subscribe(handler);
  }

  /**
   * Get the underlying agent's message history.
   */
  get messages() {
    return this.agent.state.messages;
  }

  /**
   * Get streaming state.
   */
  get isStreaming() {
    return this.agent.state.isStreaming;
  }

  /**
   * Clear conversation history.
   */
  clearMessages(): void {
    this.agent.clearMessages();
  }

  /**
   * Reset the entire agent state.
   */
  reset(): void {
    this.agent.reset();
  }

  private buildTools(): AgentTool[] {
    const capabilities = this.registry.listCapabilities();
    return buildToolsFromRegistry(
      capabilities,
      this.executor,
      this.policyEngine,
      this.auditLogger,
      this.memoryService,
      this.incidentRecorder
    );
  }
}
