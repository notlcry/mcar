/**
 * Web API request/response types.
 */

import type { Mode } from "../state/types.js";

export interface StatusResponse {
  readonly session: string;
  readonly mode: string;
  readonly apiStatus: string;
  readonly obstacle: boolean;
  readonly batteryLevel: number;
  readonly safetyLock: boolean;
  readonly lastAction?: string;
  readonly registeredModules: string[];
}

export interface CapabilityResponse {
  readonly capability_id: string;
  readonly name: string;
  readonly description: string;
  readonly risk_level: string;
  readonly inputs_schema: Record<string, unknown>;
}

export interface InvokeRequest {
  readonly capability_id: string;
  readonly params: Record<string, unknown>;
}

export interface InvokeResponse {
  readonly success: boolean;
  readonly data?: Record<string, unknown>;
  readonly error?: string;
}

export interface ChatRequest {
  readonly text: string;
}

export interface ChatResponse {
  readonly response: string;
}

export interface ModeRequest {
  readonly mode: Mode;
}

export interface MemoryResponse {
  readonly id: string;
  readonly type: string;
  readonly summary: string;
}

export interface AuditEntry {
  readonly timestamp: number;
  readonly traceId: string;
  readonly event: string;
  readonly data: Record<string, unknown>;
}

// WebSocket message types
export interface WsMessage {
  readonly type: "state_change" | "audit" | "fsm_transition" | "chat" | "stop" | "mode";
  readonly data: Record<string, unknown>;
}
