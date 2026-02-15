/**
 * ModuleProxy — high-level proxy for a remote Python module.
 *
 * Wraps ModuleBridge invoke/manifest/capabilities/health calls
 * with typed return values and error handling.
 */

import type { ModuleBridge } from "./module-bridge.js";
import type { ResultMessage, IpcError } from "./protocol.js";

export class IpcInvokeError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly userMessage?: string,
    public readonly retryable: boolean = false,
    public readonly retryAfterMs?: number,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "IpcInvokeError";
  }

  static fromIpcError(err: IpcError): IpcInvokeError {
    return new IpcInvokeError(
      err.code,
      err.message,
      err.user_message,
      err.retryable,
      err.retry_after_ms,
      err.details
    );
  }
}

export class ModuleProxy {
  constructor(
    private readonly moduleId: string,
    private readonly bridge: ModuleBridge
  ) {}

  get id(): string {
    return this.moduleId;
  }

  get isAlive(): boolean {
    return this.bridge.isModuleAlive(this.moduleId);
  }

  async invoke(
    capabilityId: string,
    params: Record<string, unknown>,
    options?: { timeoutMs?: number; idempotencyKey?: string }
  ): Promise<Record<string, unknown>> {
    const result = await this.bridge.invoke(
      this.moduleId,
      capabilityId,
      params,
      options
    );
    return this.unwrap(result);
  }

  async manifest(): Promise<Record<string, unknown>> {
    const result = await this.bridge.requestManifest(this.moduleId);
    return this.unwrap(result);
  }

  async capabilities(): Promise<Record<string, unknown>[]> {
    const result = await this.bridge.requestCapabilities(this.moduleId);
    const data = this.unwrap(result);
    return data.capabilities as Record<string, unknown>[];
  }

  async health(): Promise<Record<string, unknown>> {
    const result = await this.bridge.requestHealth(this.moduleId);
    return this.unwrap(result);
  }

  async cancel(invocationId: string): Promise<void> {
    await this.bridge.cancel(this.moduleId, invocationId);
  }

  private unwrap(result: ResultMessage): Record<string, unknown> {
    if (result.success) {
      return result.data;
    }
    throw IpcInvokeError.fromIpcError(result.error);
  }
}
