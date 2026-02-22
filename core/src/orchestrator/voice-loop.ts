/**
 * VoiceLoop — manages the voice interaction lifecycle.
 *
 * Listens for bridge events:
 * - voice.wake_word_detected → start multi-turn conversation session
 * - voice.stop_word_detected → trigger emergency stop
 *
 * Multi-turn flow after wake word:
 *   IDLE → LISTENING → THINKING → RESPONDING → LISTENING → ... → (ASR timeout) → IDLE
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
   * Handle wake word detection — enters a multi-turn conversation loop.
   *
   * Flow:
   *   1. Stop wake word detection
   *   2. Loop: ASR → dispatch → TTS → ASR → ...
   *   3. Exit loop on ASR timeout (no speech) or stop word
   *   4. Resume wake word detection
   */
  private async handleWakeWord(): Promise<void> {
    if (this.session.current !== "IDLE") {
      this.auditLogger.info("voice-loop", "wake_word.ignored", {
        reason: `System in ${this.session.current} state`,
      });
      return;
    }

    this.auditLogger.info("voice-loop", "wake_word.detected", {});

    // Stop wake word detection for the duration of the conversation
    await this.stopListening();

    // IDLE → LISTENING
    if (!this.session.transition("LISTENING")) {
      await this.startListening();
      return;
    }

    let turnCount = 0;

    try {
      // Multi-turn conversation loop
      while (this.active) {
        const t0 = Date.now();

        // Show listening expression
        await this.safeExecute("tool.display.show_expression", {
          expression: "listening",
        });

        // ASR: recognize speech
        const tAsr = Date.now();
        const asrResult = await this.safeExecute("tool.voice.recognize", {
          language: "zh-CN",
          timeout_s: 10,
        });
        const asrMs = Date.now() - tAsr;

        if (!asrResult?.success || !asrResult.data?.text) {
          this.auditLogger.info("voice-loop", "asr.no_input", {
            asr_ms: asrMs,
            turn: turnCount,
          });
          break; // Silence timeout → exit conversation loop
        }

        const text = asrResult.data.text as string;

        // Check if stop word was detected in ASR
        if (asrResult.data.is_stop_word) {
          await this.handleStopWord();
          return; // handleStopWord manages state; skip normal cleanup
        }

        turnCount++;
        this.auditLogger.info("voice-loop", "asr.recognized", {
          text,
          asr_ms: asrMs,
          turn: turnCount,
        });

        // Show thinking expression
        await this.safeExecute("tool.display.show_expression", {
          expression: "thinking",
        });

        // LISTENING → THINKING (handled by dispatcher)
        // Dispatch to agent + play acknowledgment in parallel
        const notMute = this.stateService.getMode() !== "mute";
        const tLlm = Date.now();
        let llmMs = 0;
        let ackMs = 0;

        const [response] = await Promise.all([
          this.dispatcher.dispatch(text).then((r) => {
            llmMs = Date.now() - tLlm;
            return r;
          }),
          notMute && turnCount === 1
            ? (() => {
                const tAck = Date.now();
                return this.safeExecute("tool.voice.synthesize", { text: "嗯，" }).then((r) => {
                  ackMs = Date.now() - tAck;
                  return r;
                });
              })()
            : Promise.resolve(null),
        ]);

        this.auditLogger.info("voice-loop", "timing.llm_and_ack", {
          llm_ms: llmMs,
          ack_ms: ackMs,
          turn: turnCount,
        });

        // TTS: speak the response (if not in mute mode)
        if (notMute) {
          await this.safeExecute("tool.display.show_expression", {
            expression: "speaking",
          });
          const tTts = Date.now();
          await this.safeExecute("tool.voice.synthesize", { text: response });
          const ttsMs = Date.now() - tTts;
          this.auditLogger.info("voice-loop", "timing.cycle", {
            asr_ms: asrMs,
            llm_ms: llmMs,
            ack_ms: ackMs,
            tts_ms: ttsMs,
            total_ms: Date.now() - t0,
            turn: turnCount,
          });
        }

        // RESPONDING → LISTENING for next turn (stay in conversation)
        if (!this.session.transition("LISTENING")) {
          break; // FSM rejected transition (e.g. STOPPED state)
        }
      }

      // Show neutral expression before going idle
      await this.safeExecute("tool.display.show_expression", {
        expression: "neutral",
      });

      this.auditLogger.info("voice-loop", "session.end", { turns: turnCount });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.auditLogger.error("voice-loop", "interaction.error", {
        error: message,
        turn: turnCount,
      });
    }

    // Return to IDLE and resume wake word detection
    this.session.transition("IDLE");
    await this.startListening();
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
    // Retry in case voice module capabilities are not registered yet at startup
    for (let attempt = 0; attempt < 10; attempt++) {
      const result = await this.safeExecute("tool.voice.listen_start", {});
      if (result?.success && result.data?.ok) return;
      await new Promise((r) => setTimeout(r, 500));
    }
    console.error("[VoiceLoop] Failed to start wake word detection after retries");
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
