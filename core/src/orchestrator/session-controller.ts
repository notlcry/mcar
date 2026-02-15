/**
 * SessionController — FSM state machine.
 *
 * States:
 *   IDLE → LISTENING → THINKING → PLANNING → CONFIRMING → EXECUTING → RESPONDING → IDLE
 *   Any state → STOPPED (emergency stop, highest priority) → cooldown → IDLE
 */

import type { SessionState } from "../state/types.js";
import type { StateService } from "../state/state-service.js";
import type { StopHandler } from "../safety/stop-handler.js";

const VALID_TRANSITIONS: Record<SessionState, SessionState[]> = {
  IDLE: ["LISTENING", "THINKING", "STOPPED"],
  LISTENING: ["THINKING", "IDLE", "STOPPED"],
  THINKING: ["PLANNING", "RESPONDING", "STOPPED"],
  PLANNING: ["CONFIRMING", "EXECUTING", "RESPONDING", "STOPPED"],
  CONFIRMING: ["EXECUTING", "IDLE", "STOPPED"],
  EXECUTING: ["RESPONDING", "STOPPED"],
  RESPONDING: ["IDLE", "STOPPED"],
  STOPPED: ["IDLE"],
};

type TransitionListener = (from: SessionState, to: SessionState) => void;

export class SessionController {
  private listeners: TransitionListener[] = [];

  constructor(
    private readonly stateService: StateService,
    private readonly stopHandler: StopHandler
  ) {
    // Subscribe to emergency stop
    this.stopHandler.onStop(() => {
      this.forceTransition("STOPPED");
    });
  }

  get current(): SessionState {
    return this.stateService.getSessionState();
  }

  /**
   * Attempt a state transition. Returns true if successful.
   */
  transition(to: SessionState): boolean {
    const from = this.current;
    if (from === to) return true;

    const validTargets = VALID_TRANSITIONS[from];
    if (!validTargets?.includes(to)) {
      console.warn(`[FSM] Invalid transition: ${from} → ${to}`);
      return false;
    }

    this.stateService.setSessionState(to);
    for (const listener of this.listeners) {
      listener(from, to);
    }
    return true;
  }

  /**
   * Force transition (for emergency stop — bypasses validation).
   */
  private forceTransition(to: SessionState): void {
    const from = this.current;
    this.stateService.setSessionState(to);
    for (const listener of this.listeners) {
      listener(from, to);
    }
  }

  /**
   * Transition to IDLE after STOPPED cooldown.
   */
  async recoverFromStop(): Promise<void> {
    if (this.current !== "STOPPED") return;

    const remaining = this.stopHandler.remainingCooldownMs();
    if (remaining > 0) {
      await new Promise((resolve) => setTimeout(resolve, remaining));
    }

    this.transition("IDLE");
  }

  onTransition(listener: TransitionListener): () => void {
    this.listeners.push(listener);
    return () => {
      const idx = this.listeners.indexOf(listener);
      if (idx >= 0) this.listeners.splice(idx, 1);
    };
  }
}
