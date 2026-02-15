/**
 * Capability and Module types — mirrors Spec.md definitions.
 */

// ─── Risk levels ─────────────────────────────────────────────

export type RiskLevel = "READ_ONLY" | "NORMAL" | "DANGEROUS";

// ─── Idempotency ─────────────────────────────────────────────

export type IdempotencyMode = "NONE" | "IDEMPOTENT" | "DEDUP_ONLY";

export interface IdempotencySpec {
  readonly mode: IdempotencyMode;
  readonly key_fields: readonly string[];
  readonly ttl_ms: number;
  readonly side_effect_class?: "NO_SIDE_EFFECT" | "SOFT_SIDE_EFFECT" | "HARD_SIDE_EFFECT";
  readonly supports_cancellation?: boolean;
}

// ─── Constraints ─────────────────────────────────────────────

export interface RateLimitSpec {
  readonly qps: number;
  readonly burst: number;
}

export interface ConcurrencySpec {
  readonly max_in_flight: number;
  readonly mutex_group?: string;
}

export interface RetryPolicy {
  readonly retriable_errors: readonly string[];
  readonly max_retries: number;
  readonly backoff_ms: number;
}

export interface ConstraintsSpec {
  readonly timeout_ms: number;
  readonly rate_limit?: RateLimitSpec;
  readonly max_duration_ms?: number;
  readonly cooldown_ms?: number;
  readonly max_payload_bytes?: number;
  readonly concurrency?: ConcurrencySpec;
  readonly retry_policy?: RetryPolicy;
}

// ─── State predicates ────────────────────────────────────────

export interface StatePredicate {
  readonly key: string;
  readonly op: "==" | "!=" | ">" | ">=" | "<" | "<=" | "in";
  readonly value: unknown;
  readonly on_fail: "DENY" | "CONFIRM";
}

// ─── Permissions ─────────────────────────────────────────────

export interface PermissionsSpec {
  readonly roles_allowed: readonly string[];
  readonly confirm_required: boolean;
  readonly confirm_phrase_hint?: string;
  readonly modes_allowed?: readonly string[];
  readonly deny_when_muted?: boolean;
}

// ─── Observability ───────────────────────────────────────────

export type AuditLevel = "MINIMAL" | "STANDARD" | "VERBOSE";

export interface RedactionRule {
  readonly json_path: string;
  readonly method: "MASK" | "HASH" | "DROP";
}

export interface ObservabilitySpec {
  readonly audit_level: AuditLevel;
  readonly log_inputs: boolean;
  readonly log_outputs: boolean;
  readonly redaction: readonly RedactionRule[];
}

// ─── Capability Spec (core) ──────────────────────────────────

export interface CapabilitySpec {
  readonly capability_id: string;
  readonly name: string;
  readonly type: "tool" | "skill";
  readonly version: string;
  readonly description: string;
  readonly risk_level: RiskLevel;
  readonly inputs_schema: Record<string, unknown>;
  readonly outputs_schema: Record<string, unknown>;
  readonly constraints: ConstraintsSpec;
  readonly required_state_predicates: readonly StatePredicate[];
  readonly permissions: PermissionsSpec;
  readonly idempotency: IdempotencySpec;
  readonly observability: ObservabilitySpec;
}

// ─── Module Manifest ─────────────────────────────────────────

export interface ModuleManifest {
  readonly module_id: string;
  readonly module_version: string;
  readonly description: string;
  readonly capabilities: readonly string[];
  readonly vendor?: string;
  readonly permissions_required?: readonly string[];
}

// ─── Registry types ──────────────────────────────────────────

export interface RegisteredModule {
  readonly manifest: ModuleManifest;
  readonly capabilities: readonly CapabilitySpec[];
  enabled: boolean;
}

export interface RegisteredCapability {
  readonly spec: CapabilitySpec;
  readonly moduleId: string;
}

// ─── Error codes ─────────────────────────────────────────────

export const ERROR_CODES = {
  E_INPUT_SCHEMA: "E_INPUT_SCHEMA",
  E_POLICY_CONFIRM_REQUIRED: "E_POLICY_CONFIRM_REQUIRED",
  E_POLICY_ROLE_DENIED: "E_POLICY_ROLE_DENIED",
  E_STATE_OBSTACLE: "E_STATE_OBSTACLE",
  E_STATE_ESTOP: "E_STATE_ESTOP",
  E_STATE_BATTERY_LOW: "E_STATE_BATTERY_LOW",
  E_RATE_LIMITED: "E_RATE_LIMITED",
  E_COOLDOWN_ACTIVE: "E_COOLDOWN_ACTIVE",
  E_TIMEOUT: "E_TIMEOUT",
  E_CANCELLED: "E_CANCELLED",
  E_NOT_FOUND: "E_NOT_FOUND",
  E_DEPENDENCY_NETWORK: "E_DEPENDENCY_NETWORK",
  E_DEPENDENCY_PROVIDER: "E_DEPENDENCY_PROVIDER",
  E_INTERNAL: "E_INTERNAL",
  E_DUPLICATE: "E_DUPLICATE",
  E_CONCURRENCY: "E_CONCURRENCY",
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];
