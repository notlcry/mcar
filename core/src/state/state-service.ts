/**
 * StateService — unified state view.
 *
 * Provides a key-value store for system state that can be queried
 * by PolicyEngine (for state predicates) and ContextBuilder.
 */

import type { SessionState, StateSnapshot, Mode, ApiStatus } from "./types.js";

type StateChangeListener = (key: string, value: unknown) => void;

/** Speed limits per mode. */
const MODE_SPEED_LIMITS: Record<Mode, number> = {
  normal: 100,
  safety: 50,
  kid: 30,
  debug: 100,
  mute: 100,
};

export class StateService {
  private state = new Map<string, unknown>();
  private listeners: StateChangeListener[] = [];

  constructor() {
    // Initialize defaults
    this.set("session", "IDLE");
    this.set("obstacle", false);
    this.set("batteryLevel", 1.0);
    this.set("safetyLock", false);
    this.set("mode", "normal");
    this.set("apiStatus", "online");
  }

  get(key: string): unknown {
    return this.state.get(key);
  }

  set(key: string, value: unknown): void {
    this.state.set(key, value);
    for (const listener of this.listeners) {
      listener(key, value);
    }
  }

  getSessionState(): SessionState {
    return this.get("session") as SessionState;
  }

  setSessionState(state: SessionState): void {
    this.set("session", state);
  }

  getMode(): Mode {
    return (this.get("mode") as Mode) ?? "normal";
  }

  setMode(mode: Mode): void {
    this.set("mode", mode);
    // Apply mode-specific speed limit
    this.set("maxSpeed", MODE_SPEED_LIMITS[mode]);
  }

  getApiStatus(): ApiStatus {
    return (this.get("apiStatus") as ApiStatus) ?? "online";
  }

  setApiStatus(status: ApiStatus): void {
    this.set("apiStatus", status);
  }

  getMaxSpeed(): number {
    const mode = this.getMode();
    return MODE_SPEED_LIMITS[mode];
  }

  getSnapshot(): StateSnapshot {
    return {
      session: this.get("session") as SessionState,
      obstacle: this.get("obstacle") as boolean,
      batteryLevel: this.get("batteryLevel") as number,
      safetyLock: this.get("safetyLock") as boolean,
      mode: this.getMode(),
      apiStatus: this.getApiStatus(),
      lastAction: this.get("lastAction") as string | undefined,
      lastActionTimestamp: this.get("lastActionTimestamp") as number | undefined,
    };
  }

  onChange(listener: StateChangeListener): () => void {
    this.listeners.push(listener);
    return () => {
      const idx = this.listeners.indexOf(listener);
      if (idx >= 0) this.listeners.splice(idx, 1);
    };
  }
}
