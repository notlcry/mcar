/**
 * VoiceLoop — manages the voice interaction lifecycle.
 *
 * Listens for bridge events:
 * - voice.wake_word_detected → start recognition → dispatch to agent → TTS response
 * - voice.stop_word_detected → trigger emergency stop
 *
 * Coordinates FSM transitions:
 *   IDLE → LISTENING → THINKING → RESPONDING → IDLE
 */

import type { SessionController } from "./session-controller.js";
import type { ActionDispatcher } from "./action-dispatcher.js";
import type { ModuleBridge } from "../ipc/module-bridge.js";
import type { CapabilityExecutor } from "../capability/executor.js";
import type { StopHandler } from "../safety/stop-handler.js";
import type { StateService } from "../state/state-service.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { ModuleEvent } from "../ipc/protocol.js";

export class VoiceLoop {
  private active = false;
  private unsubscribeEvent: (() => void) | null = null;

  constructor(
    private readonly session: SessionController,
    private readonly dispatcher: ActionDispatcher,
    private readonly bridge: ModuleBridge,
    private readonly executor: CapabilityExecutor,
    private readonly stopHandler: StopHandler,
    private readonly stateService: StateService,
    private readonly auditLogger: AuditLogger
  ) {}

  /**
   * Start the voice interaction loop.
   * Subscribes to module events and begins listening for wake words.
   */
  start(): void {
    if (this.active) return;
    this.active = true;

    this.unsubscribeEvent = this.bridge.onEvent((event: ModuleEvent) => {
      this.handleEvent(event).catch((err) => {
        console.error("[VoiceLoop] Error handling event:", err);
      });
    });

    // Start wake word detection
    this.startListening().catch((err) => {
      console.error("[VoiceLoop] Failed to start listening:", err);
    });
  }

  /**
   * Stop the voice interaction loop.
   */
  stop(): void {
    this.active = false;
    if (this.unsubscribeEvent) {
      this.unsubscribeEvent();
      this.unsubscribeEvent = null;
    }

    // Stop wake word detection
    this.stopListening().catch(() => {});
  }

  private async handleEvent(event: ModuleEvent): Promise<void> {
    if (!this.active) return;

    if (event.event_type === "voice.wake_word_detected") {
      await this.handleWakeWord();
    } else if (event.event_type === "voice.stop_word_detected") {
      await this.handleStopWord();
    }
  }

  /**
   * Handle wake word detection:
   * 1. Transition FSM to LISTENING
   * 2. Invoke ASR (recognize)
   * 3. Dispatch recognized text to agent
   * 4. TTS the agent response
   * 5. Return to IDLE
   */
  private async handleWakeWord(): Promise<void> {
    if (this.session.current !== "IDLE") {
      this.auditLogger.info("voice-loop", "wake_word.ignored", {
        reason: `System in ${this.session.current} state`,
      });
      return;
    }

    this.auditLogger.info("voice-loop", "wake_word.detected", {});

    // IDLE → LISTENING
    if (!this.session.transition("LISTENING")) return;

    try {
      // Show listening expression
      await this.safeExecute("tool.display.show_expression", {
        expression: "listening",
      });

      // ASR: recognize speech
      const asrResult = await this.safeExecute("tool.voice.recognize", {
        language: "zh-CN",
        timeout_s: 10,
      });

      if (!asrResult?.success || !asrResult.data?.text) {
        this.auditLogger.info("voice-loop", "asr.no_input", {});
        // Show neutral expression and return to idle
        await this.safeExecute("tool.display.show_expression", {
          expression: "neutral",
        });
        this.session.transition("IDLE");
        return;
      }

      const text = asrResult.data.text as string;

      // Check if stop word was detected in ASR
      if (asrResult.data.is_stop_word) {
        await this.handleStopWord();
        return;
      }

      this.auditLogger.info("voice-loop", "asr.recognized", { text });

      // Show thinking expression
      await this.safeExecute("tool.display.show_expression", {
        expression: "thinking",
      });

      // LISTENING → THINKING (handled by dispatcher)
      // Dispatch to agent
      const response = await this.dispatcher.dispatch(text);

      // TTS: speak the response (if not in mute mode)
      if (this.stateService.getMode() !== "mute") {
        await this.safeExecute("tool.display.show_expression", {
          expression: "speaking",
        });
        await this.safeExecute("tool.voice.synthesize", { text: response });
      }

      // Show neutral expression
      await this.safeExecute("tool.display.show_expression", {
        expression: "neutral",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.auditLogger.error("voice-loop", "interaction.error", {
        error: message,
      });
      this.session.transition("IDLE");
    }
  }

  /**
   * Handle stop word detection: trigger emergency stop immediately.
   * Never goes through LLM.
   */
  private async handleStopWord(): Promise<void> {
    this.auditLogger.warn("voice-loop", "stop_word.detected", {});
    await this.stopHandler.triggerStop("voice");

    // TTS feedback (even during stop, this is important)
    try {
      await this.safeExecute("tool.voice.synthesize", {
        text: "Emergency stop activated.",
      });
    } catch {
      // Best effort
    }
  }

  private async startListening(): Promise<void> {
    await this.safeExecute("tool.voice.listen_start", {});
  }

  private async stopListening(): Promise<void> {
    await this.safeExecute("tool.voice.listen_stop", {});
  }

  /**
   * Execute a capability safely (catch errors, return null on failure).
   */
  private async safeExecute(
    capabilityId: string,
    params: Record<string, unknown>
  ): Promise<{ success: boolean; data?: Record<string, unknown> } | null> {
    try {
      return await this.executor.execute(capabilityId, params);
    } catch {
      return null;
    }
  }
}
