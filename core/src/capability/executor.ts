/**
 * CapabilityExecutor — parameter validation, rate limiting,
 * timeout control, idempotency dedup, and result standardization.
 */

import Ajv, { type ValidateFunction } from "ajv";
import type { CapabilityRegistry } from "./registry.js";
import type {
  CapabilitySpec,
  ErrorCode,
  RateLimitSpec,
  RetryPolicy,
} from "./types.js";
import { ERROR_CODES } from "./types.js";
import { IpcInvokeError } from "../ipc/module-proxy.js";
import type { PerformanceTracker } from "../observability/performance-tracker.js";

// ─── Execution result ────────────────────────────────────────

export interface ExecutionResult {
  readonly success: boolean;
  readonly data?: Record<string, unknown>;
  readonly error?: {
    readonly code: ErrorCode;
    readonly message: string;
    readonly user_message?: string;
    readonly retryable: boolean;
    readonly retry_after_ms?: number;
  };
  readonly duration_ms?: number;
}

// ─── Token bucket for rate limiting ─────────────────────────

class TokenBucket {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private readonly qps: number,
    private readonly burst: number
  ) {
    this.tokens = burst;
    this.lastRefill = Date.now();
  }

  tryConsume(): boolean {
    this.refill();
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return true;
    }
    return false;
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.burst, this.tokens + elapsed * this.qps);
    this.lastRefill = now;
  }
}

// ─── Idempotency cache ──────────────────────────────────────

interface CachedResult {
  readonly result: ExecutionResult;
  readonly expiresAt: number;
}

export class CapabilityExecutor {
  private readonly ajv = new (Ajv as unknown as typeof Ajv.default)({ allErrors: true, strict: false });
  private readonly rateLimiters = new Map<string, TokenBucket>();
  private readonly cooldowns = new Map<string, number>(); // capability_id → cooldown expires at
  private readonly idempotencyCache = new Map<string, CachedResult>();
  private readonly inFlight = new Map<string, number>(); // capability_id → count
  private readonly mutexLocks = new Map<string, string>(); // mutex_group → capability_id holding lock

  private performanceTracker: PerformanceTracker | null = null;

  constructor(private readonly registry: CapabilityRegistry) {}

  setPerformanceTracker(tracker: PerformanceTracker): void {
    this.performanceTracker = tracker;
  }

  /**
   * Execute a capability with all checks:
   * 1. Validate params against inputs_schema (AJV)
   * 2. Rate limit check
   * 3. Cooldown check
   * 4. Idempotency dedup
   * 5. IPC invoke
   * 6. Post-execution cooldown set
   */
  async execute(
    capabilityId: string,
    params: Record<string, unknown>,
    options?: { idempotencyKey?: string }
  ): Promise<ExecutionResult> {
    // Look up capability
    const registered = this.registry.getCapability(capabilityId);
    if (!registered) {
      return this.fail(ERROR_CODES.E_NOT_FOUND, `Capability not found: ${capabilityId}`);
    }

    const spec = registered.spec;
    const proxy = this.registry.getProxy(registered.moduleId);
    if (!proxy) {
      return this.fail(ERROR_CODES.E_NOT_FOUND, `Module not found: ${registered.moduleId}`);
    }

    // 1. Validate params
    const validationError = this.validateParams(spec, params);
    if (validationError) {
      return this.fail(ERROR_CODES.E_INPUT_SCHEMA, validationError);
    }

    // 2. Rate limit
    const rateLimitError = this.checkRateLimit(spec);
    if (rateLimitError) return rateLimitError;

    // 3. Cooldown
    const cooldownError = this.checkCooldown(spec);
    if (cooldownError) return cooldownError;

    // 4. Idempotency dedup
    const idempotencyKey = options?.idempotencyKey ?? this.computeIdempotencyKey(spec, params);
    if (idempotencyKey) {
      const cached = this.checkIdempotency(spec, idempotencyKey);
      if (cached) return cached;
    }

    // 5. Concurrency check
    const concurrencyError = this.checkConcurrency(spec);
    if (concurrencyError) return concurrencyError;

    // 6. Acquire concurrency slot
    this.acquireConcurrency(spec);

    // 7. Invoke via IPC (with retry)
    const startTime = Date.now();
    const retryPolicy = spec.constraints.retry_policy;
    const maxAttempts = retryPolicy ? retryPolicy.max_retries + 1 : 1;

    try {
      let lastError: Error | undefined;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          const data = await proxy.invoke(capabilityId, params, {
            timeoutMs: spec.constraints.timeout_ms,
            idempotencyKey: idempotencyKey ?? undefined,
          });

          const duration_ms = Date.now() - startTime;
          this.performanceTracker?.record(`executor.${capabilityId}`, duration_ms);
          const result: ExecutionResult = { success: true, data, duration_ms };

          // Cache for idempotency
          if (idempotencyKey && spec.idempotency.mode !== "NONE") {
            this.cacheResult(idempotencyKey, result, spec.idempotency.ttl_ms);
          }

          // Set cooldown
          if (spec.constraints.cooldown_ms) {
            this.cooldowns.set(capabilityId, Date.now() + spec.constraints.cooldown_ms);
          }

          return result;
        } catch (err) {
          lastError = err instanceof Error ? err : new Error(String(err));

          if (attempt < maxAttempts && retryPolicy && this.shouldRetry(lastError, retryPolicy)) {
            const delayMs = retryPolicy.backoff_ms * Math.pow(2, attempt - 1);
            await this.sleep(delayMs);
            continue;
          }

          break;
        }
      }

      const message = lastError?.message ?? "Unknown error";
      const duration_ms = Date.now() - startTime;
      this.performanceTracker?.record(`executor.${capabilityId}`, duration_ms);
      return { ...this.fail(ERROR_CODES.E_INTERNAL, message, true), duration_ms };
    } finally {
      this.releaseConcurrency(spec);
    }
  }

  // ─── Validation ───────────────────────────────────────────

  private validateParams(spec: CapabilitySpec, params: Record<string, unknown>): string | null {
    if (!spec.inputs_schema || Object.keys(spec.inputs_schema).length === 0) {
      return null;
    }

    const validate = this.ajv.compile(spec.inputs_schema);
    if (validate(params)) {
      return null;
    }

    const errors = validate.errors?.map((e: { instancePath: string; message?: string }) => `${e.instancePath} ${e.message}`).join("; ");
    return `Parameter validation failed: ${errors}`;
  }

  // ─── Rate limiting ────────────────────────────────────────

  private checkRateLimit(spec: CapabilitySpec): ExecutionResult | null {
    const rl = spec.constraints.rate_limit;
    if (!rl) return null;

    const key = spec.capability_id;
    let bucket = this.rateLimiters.get(key);
    if (!bucket) {
      bucket = new TokenBucket(rl.qps, rl.burst);
      this.rateLimiters.set(key, bucket);
    }

    if (!bucket.tryConsume()) {
      return {
        success: false,
        error: {
          code: ERROR_CODES.E_RATE_LIMITED,
          message: `Rate limit exceeded for ${spec.capability_id}`,
          retryable: true,
          retry_after_ms: Math.ceil(1000 / rl.qps),
        },
      };
    }

    return null;
  }

  // ─── Cooldown ─────────────────────────────────────────────

  private checkCooldown(spec: CapabilitySpec): ExecutionResult | null {
    const expiresAt = this.cooldowns.get(spec.capability_id);
    if (!expiresAt) return null;

    const remaining = expiresAt - Date.now();
    if (remaining <= 0) {
      this.cooldowns.delete(spec.capability_id);
      return null;
    }

    return {
      success: false,
      error: {
        code: ERROR_CODES.E_COOLDOWN_ACTIVE,
        message: `Cooldown active for ${spec.capability_id}, ${remaining}ms remaining`,
        retryable: true,
        retry_after_ms: remaining,
      },
    };
  }

  // ─── Idempotency ──────────────────────────────────────────

  private computeIdempotencyKey(
    spec: CapabilitySpec,
    params: Record<string, unknown>
  ): string | null {
    if (spec.idempotency.mode === "NONE") return null;
    if (spec.idempotency.key_fields.length === 0) return spec.capability_id;

    const keyParts = spec.idempotency.key_fields.map((field) =>
      JSON.stringify(params[field] ?? null)
    );
    return `${spec.capability_id}:${keyParts.join(":")}`;
  }

  private checkIdempotency(spec: CapabilitySpec, key: string): ExecutionResult | null {
    // Clean expired entries
    this.cleanExpiredIdempotency();

    const cached = this.idempotencyCache.get(key);
    if (!cached) return null;

    if (spec.idempotency.mode === "DEDUP_ONLY") {
      return {
        success: false,
        error: {
          code: ERROR_CODES.E_DUPLICATE,
          message: `Duplicate request for ${spec.capability_id}`,
          retryable: false,
        },
      };
    }

    // IDEMPOTENT: return cached result
    return cached.result;
  }

  private cacheResult(key: string, result: ExecutionResult, ttlMs: number): void {
    if (ttlMs <= 0) return;
    this.idempotencyCache.set(key, {
      result,
      expiresAt: Date.now() + ttlMs,
    });
  }

  private cleanExpiredIdempotency(): void {
    const now = Date.now();
    for (const [key, entry] of this.idempotencyCache) {
      if (entry.expiresAt <= now) {
        this.idempotencyCache.delete(key);
      }
    }
  }

  // ─── Concurrency ─────────────────────────────────────────

  private checkConcurrency(spec: CapabilitySpec): ExecutionResult | null {
    const conc = spec.constraints.concurrency;
    if (!conc) return null;

    // Check max_in_flight per capability
    const current = this.inFlight.get(spec.capability_id) ?? 0;
    if (current >= conc.max_in_flight) {
      return {
        success: false,
        error: {
          code: ERROR_CODES.E_CONCURRENCY,
          message: `Max in-flight (${conc.max_in_flight}) reached for ${spec.capability_id}`,
          retryable: true,
          retry_after_ms: 500,
        },
      };
    }

    // Check mutex group
    if (conc.mutex_group) {
      const holder = this.mutexLocks.get(conc.mutex_group);
      if (holder && holder !== spec.capability_id) {
        return {
          success: false,
          error: {
            code: ERROR_CODES.E_CONCURRENCY,
            message: `Mutex group '${conc.mutex_group}' locked by ${holder}`,
            retryable: true,
            retry_after_ms: 500,
          },
        };
      }
    }

    return null;
  }

  private acquireConcurrency(spec: CapabilitySpec): void {
    const conc = spec.constraints.concurrency;
    if (!conc) return;

    const current = this.inFlight.get(spec.capability_id) ?? 0;
    this.inFlight.set(spec.capability_id, current + 1);

    if (conc.mutex_group) {
      this.mutexLocks.set(conc.mutex_group, spec.capability_id);
    }
  }

  private releaseConcurrency(spec: CapabilitySpec): void {
    const conc = spec.constraints.concurrency;
    if (!conc) return;

    const current = this.inFlight.get(spec.capability_id) ?? 0;
    if (current <= 1) {
      this.inFlight.delete(spec.capability_id);
    } else {
      this.inFlight.set(spec.capability_id, current - 1);
    }

    if (conc.mutex_group) {
      const holder = this.mutexLocks.get(conc.mutex_group);
      if (holder === spec.capability_id && (this.inFlight.get(spec.capability_id) ?? 0) === 0) {
        this.mutexLocks.delete(conc.mutex_group);
      }
    }
  }

  // ─── Retry helpers ──────────────────────────────────────

  private shouldRetry(error: Error, retryPolicy: RetryPolicy): boolean {
    const errorCode = this.extractErrorCode(error);
    return retryPolicy.retriable_errors.includes(errorCode);
  }

  private extractErrorCode(error: Error): string {
    if (error instanceof IpcInvokeError) {
      return error.code;
    }
    if (error.message.includes("timeout") || error.message.includes("TIMEOUT")) {
      return ERROR_CODES.E_TIMEOUT;
    }
    return ERROR_CODES.E_INTERNAL;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // ─── Helpers ──────────────────────────────────────────────

  private fail(
    code: ErrorCode,
    message: string,
    retryable = false,
    retryAfterMs?: number
  ): ExecutionResult {
    return {
      success: false,
      error: { code, message, retryable, retry_after_ms: retryAfterMs },
    };
  }
}
