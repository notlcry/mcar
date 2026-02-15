/**
 * IPC Protocol — ZeroMQ message envelope types.
 *
 * Main channel (ROUTER-DEALER):
 *   Node.js ROUTER ←→ Python DEALER per module
 *
 * Emergency stop channel (PUB-SUB):
 *   Node.js PUB → all Python SUB subscribers
 */

// ─── Request messages (Node.js → Python) ────────────────────────

export interface InvokeRequest {
  readonly type: "invoke";
  readonly id: string;
  readonly capability_id: string;
  readonly params: Record<string, unknown>;
  readonly idempotency_key?: string;
  readonly timeout_ms?: number;
}

export interface ManifestRequest {
  readonly type: "manifest";
  readonly id: string;
}

export interface CapabilitiesRequest {
  readonly type: "capabilities";
  readonly id: string;
}

export interface HealthRequest {
  readonly type: "health";
  readonly id: string;
}

export interface CancelRequest {
  readonly type: "cancel";
  readonly id: string;
  readonly invocation_id: string;
}

export type RequestMessage =
  | InvokeRequest
  | ManifestRequest
  | CapabilitiesRequest
  | HealthRequest
  | CancelRequest;

// ─── Response messages (Python → Node.js) ────────────────────────

export interface SuccessResult {
  readonly type: "result";
  readonly id: string;
  readonly success: true;
  readonly data: Record<string, unknown>;
}

export interface ErrorResult {
  readonly type: "result";
  readonly id: string;
  readonly success: false;
  readonly error: IpcError;
}

export type ResultMessage = SuccessResult | ErrorResult;

export interface IpcError {
  readonly code: string;
  readonly message: string;
  readonly user_message?: string;
  readonly details?: Record<string, unknown>;
  readonly retryable: boolean;
  readonly retry_after_ms?: number;
}

// ─── Event messages (Python → Node.js, unsolicited) ─────────────

export interface ModuleEvent {
  readonly type: "event";
  readonly source: string;
  readonly event_type: string;
  readonly data: Record<string, unknown>;
  readonly timestamp: number;
}

// ─── Registration (Python → Node.js, on connect) ────────────────

export interface RegisterMessage {
  readonly type: "register";
  readonly module_id: string;
}

// ─── Heartbeat ───────────────────────────────────────────────────

export interface HeartbeatPing {
  readonly type: "heartbeat_ping";
  readonly id: string;
  readonly timestamp: number;
}

export interface HeartbeatPong {
  readonly type: "heartbeat_pong";
  readonly id: string;
  readonly timestamp: number;
}

// ─── Emergency stop (PUB channel) ────────────────────────────────

export interface StopBroadcast {
  readonly type: "stop";
  readonly source: "voice" | "web" | "system";
  readonly timestamp: number;
}

// ─── Union types ─────────────────────────────────────────────────

export type InboundMessage =
  | ResultMessage
  | ModuleEvent
  | RegisterMessage
  | HeartbeatPong;

export type OutboundMessage =
  | RequestMessage
  | HeartbeatPing;

// ─── Serialization helpers ───────────────────────────────────────

export function encodeMessage(msg: unknown): Buffer {
  return Buffer.from(JSON.stringify(msg), "utf-8");
}

export function decodeMessage<T = unknown>(buf: Buffer): T {
  return JSON.parse(buf.toString("utf-8")) as T;
}
