/**
 * ModuleBridge — ZeroMQ ROUTER + PUB server.
 *
 * Manages connections from Python module processes:
 * - ROUTER socket receives registration, results, events, heartbeat pongs
 * - PUB socket broadcasts emergency stop to all modules
 */

import { Router, Publisher } from "zeromq";
import { v4 as uuid } from "uuid";
import type { IpcConfig } from "../config/config.js";
import {
  type InboundMessage,
  type InvokeRequest,
  type ManifestRequest,
  type CapabilitiesRequest,
  type HealthRequest,
  type CancelRequest,
  type StopBroadcast,
  type HeartbeatPing,
  type ResultMessage,
  type ModuleEvent,
  type RegisterMessage,
  encodeMessage,
  decodeMessage,
} from "./protocol.js";

export interface PendingRequest {
  readonly id: string;
  readonly moduleId: string;
  resolve: (result: ResultMessage) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export interface ModuleInfo {
  readonly moduleId: string;
  identity: Buffer;
  lastHeartbeat: number;
}

type EventHandler = (event: ModuleEvent) => void;
type RegisterHandler = (moduleId: string) => void;

export class ModuleBridge {
  private router: Router | null = null;
  private publisher: Publisher | null = null;
  private modules = new Map<string, ModuleInfo>();
  private pending = new Map<string, PendingRequest>();
  private eventHandlers: EventHandler[] = [];
  private registerHandlers: RegisterHandler[] = [];
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private running = false;

  constructor(private readonly config: IpcConfig) {}

  async start(): Promise<void> {
    this.router = new Router();
    this.publisher = new Publisher();

    await this.router.bind(this.config.routerEndpoint);
    await this.publisher.bind(this.config.pubEndpoint);

    this.running = true;
    this.receiveLoop();
    this.startHeartbeat();
  }

  async stop(): Promise<void> {
    this.running = false;

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    for (const [, req] of this.pending) {
      clearTimeout(req.timer);
      req.reject(new Error("Bridge shutting down"));
    }
    this.pending.clear();

    if (this.router) {
      this.router.close();
      this.router = null;
    }
    if (this.publisher) {
      this.publisher.close();
      this.publisher = null;
    }
  }

  onEvent(handler: EventHandler): () => void {
    this.eventHandlers.push(handler);
    return () => {
      const idx = this.eventHandlers.indexOf(handler);
      if (idx >= 0) this.eventHandlers.splice(idx, 1);
    };
  }

  onRegister(handler: RegisterHandler): () => void {
    this.registerHandlers.push(handler);
    return () => {
      const idx = this.registerHandlers.indexOf(handler);
      if (idx >= 0) this.registerHandlers.splice(idx, 1);
    };
  }

  getRegisteredModules(): string[] {
    return [...this.modules.keys()];
  }

  isModuleAlive(moduleId: string): boolean {
    const mod = this.modules.get(moduleId);
    if (!mod) return false;
    return Date.now() - mod.lastHeartbeat < this.config.heartbeatTimeoutMs;
  }

  /**
   * Send an invoke request to a module and wait for the result.
   */
  async invoke(
    moduleId: string,
    capabilityId: string,
    params: Record<string, unknown>,
    options?: { timeoutMs?: number; idempotencyKey?: string }
  ): Promise<ResultMessage> {
    const mod = this.modules.get(moduleId);
    if (!mod) {
      throw new Error(`Module not registered: ${moduleId}`);
    }

    const id = uuid();
    const timeoutMs = options?.timeoutMs ?? this.config.invokeTimeoutMs;

    const request: InvokeRequest = {
      type: "invoke",
      id,
      capability_id: capabilityId,
      params,
      idempotency_key: options?.idempotencyKey,
      timeout_ms: timeoutMs,
    };

    return this.sendAndWait(mod.identity, id, request, timeoutMs);
  }

  /**
   * Request the manifest from a module.
   */
  async requestManifest(moduleId: string): Promise<ResultMessage> {
    const mod = this.modules.get(moduleId);
    if (!mod) throw new Error(`Module not registered: ${moduleId}`);

    const id = uuid();
    const request: ManifestRequest = { type: "manifest", id };
    return this.sendAndWait(mod.identity, id, request, this.config.invokeTimeoutMs);
  }

  /**
   * Request capabilities from a module.
   */
  async requestCapabilities(moduleId: string): Promise<ResultMessage> {
    const mod = this.modules.get(moduleId);
    if (!mod) throw new Error(`Module not registered: ${moduleId}`);

    const id = uuid();
    const request: CapabilitiesRequest = { type: "capabilities", id };
    return this.sendAndWait(mod.identity, id, request, this.config.invokeTimeoutMs);
  }

  /**
   * Request health status from a module.
   */
  async requestHealth(moduleId: string): Promise<ResultMessage> {
    const mod = this.modules.get(moduleId);
    if (!mod) throw new Error(`Module not registered: ${moduleId}`);

    const id = uuid();
    const request: HealthRequest = { type: "health", id };
    return this.sendAndWait(mod.identity, id, request, this.config.invokeTimeoutMs);
  }

  /**
   * Cancel an in-flight invocation.
   */
  async cancel(moduleId: string, invocationId: string): Promise<ResultMessage> {
    const mod = this.modules.get(moduleId);
    if (!mod) throw new Error(`Module not registered: ${moduleId}`);

    const id = uuid();
    const request: CancelRequest = {
      type: "cancel",
      id,
      invocation_id: invocationId,
    };
    return this.sendAndWait(mod.identity, id, request, 5000);
  }

  /**
   * Broadcast emergency stop to all modules via PUB socket.
   */
  async broadcastStop(source: StopBroadcast["source"]): Promise<void> {
    if (!this.publisher) throw new Error("Bridge not started");

    const msg: StopBroadcast = {
      type: "stop",
      source,
      timestamp: Date.now(),
    };

    await this.publisher.send(["stop", encodeMessage(msg)]);
  }

  // ─── Internal ────────────────────────────────────────────────

  private async sendAndWait(
    identity: Buffer,
    id: string,
    request: unknown,
    timeoutMs: number
  ): Promise<ResultMessage> {
    if (!this.router) throw new Error("Bridge not started");

    return new Promise<ResultMessage>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Request ${id} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pending.set(id, {
        id,
        moduleId: "",
        resolve,
        reject,
        timer,
      });

      this.router!.send([identity, Buffer.alloc(0), encodeMessage(request)]).catch((err) => {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(err);
      });
    });
  }

  private async receiveLoop(): Promise<void> {
    if (!this.router) return;

    while (this.running) {
      try {
        const [identity, , payload] = await this.router.receive();
        const msg = decodeMessage<InboundMessage>(Buffer.from(payload));
        this.handleMessage(Buffer.from(identity), msg);
      } catch (err) {
        if (this.running) {
          console.error("[ModuleBridge] receive error:", err);
        }
      }
    }
  }

  private handleMessage(identity: Buffer, msg: InboundMessage): void {
    switch (msg.type) {
      case "register":
        this.handleRegister(identity, msg as RegisterMessage);
        break;
      case "result":
        this.handleResult(msg as ResultMessage);
        break;
      case "event":
        this.handleEvent(msg as ModuleEvent);
        break;
      case "heartbeat_pong":
        this.handleHeartbeatPong(identity);
        break;
    }
  }

  private handleRegister(identity: Buffer, msg: RegisterMessage): void {
    this.modules.set(msg.module_id, {
      moduleId: msg.module_id,
      identity,
      lastHeartbeat: Date.now(),
    });
    for (const handler of this.registerHandlers) {
      handler(msg.module_id);
    }
  }

  private handleResult(msg: ResultMessage): void {
    const req = this.pending.get(msg.id);
    if (req) {
      clearTimeout(req.timer);
      this.pending.delete(msg.id);
      req.resolve(msg);
    }
  }

  private handleEvent(msg: ModuleEvent): void {
    for (const handler of this.eventHandlers) {
      handler(msg);
    }
  }

  private handleHeartbeatPong(identity: Buffer): void {
    for (const [, mod] of this.modules) {
      if (mod.identity.equals(identity)) {
        mod.lastHeartbeat = Date.now();
        break;
      }
    }
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeats();
    }, this.config.heartbeatIntervalMs);
  }

  private async sendHeartbeats(): Promise<void> {
    if (!this.router) return;

    const ping: HeartbeatPing = {
      type: "heartbeat_ping",
      id: uuid(),
      timestamp: Date.now(),
    };

    for (const [, mod] of this.modules) {
      try {
        await this.router.send([mod.identity, Buffer.alloc(0), encodeMessage(ping)]);
      } catch {
        // Module may have disconnected
      }
    }
  }
}
