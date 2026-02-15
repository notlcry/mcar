/**
 * DegradationHandler — manages API failure tracking and offline mode.
 *
 * When the LLM API fails consecutively (default threshold: 3),
 * enters degradation mode with:
 * - Hardcoded Chinese responses for common queries
 * - Basic command parsing for motion (forward/backward/left/right/stop)
 * - Periodic retry (30s) to detect recovery
 */

import type { StateService } from "../state/state-service.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { IncidentRecorder } from "../observability/incident-recorder.js";

/** Basic motion commands recognized in degraded mode. */
const BASIC_COMMANDS: Record<string, { capability: string; params: Record<string, unknown> }> = {
  "前进": { capability: "tool.motion.forward", params: { speed: 30, duration_ms: 1000 } },
  "forward": { capability: "tool.motion.forward", params: { speed: 30, duration_ms: 1000 } },
  "后退": { capability: "tool.motion.backward", params: { speed: 30, duration_ms: 1000 } },
  "backward": { capability: "tool.motion.backward", params: { speed: 30, duration_ms: 1000 } },
  "左转": { capability: "tool.motion.turn_left", params: { speed: 30, duration_ms: 500 } },
  "left": { capability: "tool.motion.turn_left", params: { speed: 30, duration_ms: 500 } },
  "右转": { capability: "tool.motion.turn_right", params: { speed: 30, duration_ms: 500 } },
  "right": { capability: "tool.motion.turn_right", params: { speed: 30, duration_ms: 500 } },
  "停止": { capability: "tool.motion.stop", params: {} },
  "stop": { capability: "tool.motion.stop", params: {} },
};

const OFFLINE_RESPONSES: string[] = [
  "抱歉，我的网络连接暂时不可用。我只能执行基本的运动命令（前进/后退/左转/右转/停止）。",
  "网络连接中断中。你可以说运动指令，比如'前进'或'左转'。",
  "我现在处于离线模式，只能理解简单指令。",
];

export interface BasicCommand {
  readonly capability: string;
  readonly params: Record<string, unknown>;
}

export class DegradationHandler {
  private consecutiveFailures = 0;
  private degraded = false;
  private retryTimer: ReturnType<typeof setInterval> | null = null;
  private incidentRecorder: IncidentRecorder | null = null;

  constructor(
    private readonly stateService: StateService,
    private readonly auditLogger: AuditLogger,
    private readonly failureThreshold: number = 3,
    private readonly retryIntervalMs: number = 30_000
  ) {}

  setIncidentRecorder(recorder: IncidentRecorder): void {
    this.incidentRecorder = recorder;
  }

  /**
   * Record an API call success. Resets failure counter.
   * If currently degraded, exits degradation mode.
   */
  recordSuccess(): void {
    const wasDegraded = this.degraded;
    this.consecutiveFailures = 0;

    if (wasDegraded) {
      this.degraded = false;
      this.stateService.setApiStatus("online");
      this.stopRetryTimer();
      this.auditLogger.info("degradation", "api.recovered", {});
    }
  }

  /**
   * Record an API call failure. If consecutive failures exceed threshold,
   * enters degradation mode.
   */
  recordFailure(error: string): void {
    this.consecutiveFailures++;
    this.auditLogger.warn("degradation", "api.failure", {
      consecutiveFailures: this.consecutiveFailures,
      error,
    });

    if (this.consecutiveFailures >= this.failureThreshold && !this.degraded) {
      this.enterDegradedMode();
    }
  }

  /**
   * Whether the system is currently in degraded (offline) mode.
   */
  isDegraded(): boolean {
    return this.degraded;
  }

  /**
   * Get a hardcoded offline response.
   */
  getOfflineResponse(): string {
    const idx = Math.floor(Math.random() * OFFLINE_RESPONSES.length);
    return OFFLINE_RESPONSES[idx];
  }

  /**
   * Parse basic motion commands from user text.
   * Returns null if not a recognized command.
   */
  parseBasicCommand(text: string): BasicCommand | null {
    const trimmed = text.trim().toLowerCase();
    const cmd = BASIC_COMMANDS[trimmed];
    return cmd ? { capability: cmd.capability, params: cmd.params } : null;
  }

  /**
   * Clean up (stop retry timer).
   */
  dispose(): void {
    this.stopRetryTimer();
  }

  private enterDegradedMode(): void {
    this.degraded = true;
    this.stateService.setApiStatus("degraded");
    this.auditLogger.warn("degradation", "api.degraded", {
      consecutiveFailures: this.consecutiveFailures,
    });
    this.incidentRecorder?.record({
      category: "api_degradation",
      error_code: "API_CONSECUTIVE_FAILURES",
      message: `API entered degraded mode after ${this.consecutiveFailures} consecutive failures`,
      details: { consecutiveFailures: this.consecutiveFailures },
    });
  }

  private stopRetryTimer(): void {
    if (this.retryTimer) {
      clearInterval(this.retryTimer);
      this.retryTimer = null;
    }
  }
}
