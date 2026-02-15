/**
 * ActionDispatcher — receives user input and drives the agent loop.
 *
 * Coordinates:
 * - SessionController (FSM transitions)
 * - AgentRuntime (LLM + tool execution)
 * - AuditLogger (tracing)
 * - CONFIRMING flow (dangerous action confirmation)
 */

import { v4 as uuid } from "uuid";
import type { AgentEvent } from "@mariozechner/pi-agent-core";
import type { SessionController } from "./session-controller.js";
import type { AgentRuntime } from "../agent/agent-runtime.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { StopHandler } from "../safety/stop-handler.js";
import type { PerformanceTracker } from "../observability/performance-tracker.js";
import type { MemoryService } from "../memory/memory-service.js";
import type { MemoryType } from "../memory/types.js";

const STOP_WORDS = new Set(["stop", "halt", "emergency", "estop", "停", "停止", "急停"]);
const CONFIRM_WORDS = new Set(["是", "确认", "yes", "confirm", "ok", "好"]);
const REJECT_WORDS = new Set(["否", "取消", "no", "cancel", "算了"]);

const CONFIRM_TIMEOUT_MS = 15_000;

export interface PendingConfirmation {
  readonly id: string;
  readonly reason: string;
  readonly hint?: string;
  readonly timestamp: number;
  resolve: (confirmed: boolean) => void;
}

export interface MemoryProposal {
  readonly type: string;
  readonly summary: string;
  readonly content?: string;
}

export class ActionDispatcher {
  private pendingConfirmation: PendingConfirmation | null = null;
  private pendingMemoryProposal: MemoryProposal | null = null;

  constructor(
    private readonly session: SessionController,
    private readonly agent: AgentRuntime,
    private readonly auditLogger: AuditLogger,
    private readonly stopHandler: StopHandler,
    private readonly performanceTracker?: PerformanceTracker,
    private readonly memoryService?: MemoryService
  ) {}

  /**
   * Process a user text input.
   */
  async dispatch(text: string): Promise<string> {
    const traceId = uuid();
    const trimmed = text.trim().toLowerCase();

    // Check for stop words — hardcoded, highest priority
    if (STOP_WORDS.has(trimmed)) {
      await this.stopHandler.triggerStop("voice");
      return "Emergency stop activated. All operations halted.";
    }

    // Check for pending confirmation response
    if (this.pendingConfirmation) {
      return this.handleConfirmationResponse(trimmed);
    }

    // FSM: IDLE → THINKING
    if (!this.session.transition("THINKING")) {
      return `Cannot process: system is in ${this.session.current} state.`;
    }

    this.auditLogger.info(traceId, "dispatch.start", { text });
    const finishTimer = this.performanceTracker?.startTimer("dispatch.cycle");

    try {
      // Collect the assistant's response
      let responseText = "";

      const unsubscribe = this.agent.subscribe((event: AgentEvent) => {
        if (
          event.type === "message_update" &&
          event.assistantMessageEvent.type === "text_delta"
        ) {
          responseText += event.assistantMessageEvent.delta;
        }
      });

      // FSM: THINKING → (agent processes, may call tools → EXECUTING)
      await this.agent.prompt(text);

      unsubscribe();

      finishTimer?.();

      this.auditLogger.info(traceId, "dispatch.complete", {
        responseLength: responseText.length,
      });

      // FSM: → RESPONDING → IDLE
      this.session.transition("RESPONDING");
      this.session.transition("IDLE");

      return responseText || "(no response)";
    } catch (err) {
      finishTimer?.();
      const message = err instanceof Error ? err.message : String(err);
      this.auditLogger.error(traceId, "dispatch.error", { error: message });
      this.session.transition("IDLE");
      return `Error: ${message}`;
    }
  }

  /**
   * Start a confirmation flow. Returns a promise that resolves to
   * the user's confirmation text response.
   */
  requestConfirmation(reason: string, hint?: string): Promise<boolean> {
    // Cancel any existing pending confirmation
    if (this.pendingConfirmation) {
      this.pendingConfirmation.resolve(false);
    }

    return new Promise<boolean>((resolve) => {
      this.pendingConfirmation = {
        id: uuid(),
        reason,
        hint,
        timestamp: Date.now(),
        resolve,
      };

      // Auto-reject after timeout
      setTimeout(() => {
        if (this.pendingConfirmation?.id === this.pendingConfirmation?.id) {
          this.pendingConfirmation?.resolve(false);
          this.pendingConfirmation = null;
          this.session.transition("IDLE");
        }
      }, CONFIRM_TIMEOUT_MS);
    });
  }

  /**
   * Start a memory proposal confirmation flow.
   * On user confirm, the memory is written to MemoryService.
   */
  requestMemoryConfirmation(proposal: MemoryProposal): Promise<boolean> {
    this.pendingMemoryProposal = proposal;
    return this.requestConfirmation(
      `Remember: "${proposal.summary}" (${proposal.type})`,
      "Say yes to save, no to discard."
    );
  }

  /**
   * Check if there's a pending confirmation.
   */
  getPendingConfirmation(): PendingConfirmation | null {
    return this.pendingConfirmation;
  }

  private handleConfirmationResponse(text: string): string {
    const pending = this.pendingConfirmation;
    if (!pending) return "No pending confirmation.";

    const memoryProposal = this.pendingMemoryProposal;
    this.pendingConfirmation = null;
    this.pendingMemoryProposal = null;

    if (CONFIRM_WORDS.has(text)) {
      pending.resolve(true);
      this.auditLogger.info("system", "confirm.accepted", {
        reason: pending.reason,
      });

      // Write memory if this was a memory proposal confirmation
      if (memoryProposal && this.memoryService) {
        const contentObj = memoryProposal.content
          ? JSON.parse(memoryProposal.content)
          : {};
        this.memoryService.create({
          type: memoryProposal.type as MemoryType,
          content: contentObj,
          summary: memoryProposal.summary,
          source: "agent_proposed",
        });
        this.auditLogger.info("system", "memory.proposal.saved", {
          type: memoryProposal.type,
          summary: memoryProposal.summary,
        });
        return "Confirmed. Memory saved.";
      }

      return "Confirmed. Executing...";
    }

    if (REJECT_WORDS.has(text)) {
      pending.resolve(false);
      this.auditLogger.info("system", "confirm.rejected", {
        reason: pending.reason,
      });
      this.session.transition("IDLE");
      return "Cancelled.";
    }

    // Unrecognized → treat as rejection
    pending.resolve(false);
    this.session.transition("IDLE");
    return "Confirmation cancelled (unrecognized response).";
  }
}
