/**
 * State Service types.
 */

export type SessionState =
  | "IDLE"
  | "LISTENING"
  | "THINKING"
  | "PLANNING"
  | "CONFIRMING"
  | "EXECUTING"
  | "RESPONDING"
  | "STOPPED";

export type Mode = "normal" | "safety" | "kid" | "debug" | "mute";

export type ApiStatus = "online" | "degraded" | "offline";

export interface StateSnapshot {
  readonly session: SessionState;
  readonly obstacle: boolean;
  readonly batteryLevel: number;
  readonly safetyLock: boolean;
  readonly mode: Mode;
  readonly apiStatus: ApiStatus;
  readonly lastAction?: string;
  readonly lastActionTimestamp?: number;
}
