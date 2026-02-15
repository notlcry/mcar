/**
 * StopHandler — emergency stop broadcast + safety_lock management.
 *
 * When an emergency stop is triggered:
 * 1. Broadcasts "stop" on PUB channel to all modules
 * 2. Sets safety_lock for cooldown period
 * 3. During cooldown, all non-READ_ONLY operations are blocked
 */

import type { ModuleBridge } from "../ipc/module-bridge.js";
import type { SafetyConfig } from "../config/config.js";
import type { SafetyState } from "./types.js";

type StopListener = () => void;

export class StopHandler {
  private readonly state: SafetyState = {
    safetyLock: false,
    safetyLockExpiresAt: 0,
  };
  private listeners: StopListener[] = [];

  constructor(
    private readonly bridge: ModuleBridge,
    private readonly config: SafetyConfig
  ) {}

  /**
   * Trigger emergency stop.
   */
  async triggerStop(source: "voice" | "web" | "system" | "button"): Promise<void> {
    // Set safety lock
    this.state.safetyLock = true;
    this.state.safetyLockExpiresAt = Date.now() + this.config.estopCooldownMs;

    // Broadcast to all modules
    await this.bridge.broadcastStop(source);

    // Notify listeners
    for (const listener of this.listeners) {
      listener();
    }

    // Auto-release lock after cooldown
    setTimeout(() => {
      if (Date.now() >= this.state.safetyLockExpiresAt) {
        this.state.safetyLock = false;
      }
    }, this.config.estopCooldownMs);
  }

  /**
   * Check if safety lock is currently active.
   */
  isLocked(): boolean {
    if (!this.state.safetyLock) return false;

    // Check if lock has expired
    if (Date.now() >= this.state.safetyLockExpiresAt) {
      this.state.safetyLock = false;
      return false;
    }

    return true;
  }

  /**
   * Get remaining cooldown time in ms. Returns 0 if not locked.
   */
  remainingCooldownMs(): number {
    if (!this.isLocked()) return 0;
    return Math.max(0, this.state.safetyLockExpiresAt - Date.now());
  }

  /**
   * Subscribe to stop events.
   */
  onStop(listener: StopListener): () => void {
    this.listeners.push(listener);
    return () => {
      const idx = this.listeners.indexOf(listener);
      if (idx >= 0) this.listeners.splice(idx, 1);
    };
  }
}
