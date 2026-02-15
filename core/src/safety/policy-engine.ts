/**
 * PolicyEngine — risk-based access control chain.
 *
 * Check order (sequential, first failure → reject):
 * 1. Emergency stop lock
 * 2. Mute mode check (deny_when_muted capabilities)
 * 3. State predicates (e.g., obstacle == false)
 * 4. Risk level gates:
 *    - READ_ONLY → allow (audit only)
 *    - NORMAL → param bounds + rate limit (handled by executor)
 *    - DANGEROUS → confirm_required / role_required / state_gate
 * 5. Permission checks (roles, modes)
 * 6. Device memory constraints (speed limits, etc.)
 */

import type { CapabilitySpec, StatePredicate } from "../capability/types.js";
import { ERROR_CODES } from "../capability/types.js";
import type { StopHandler } from "./stop-handler.js";
import type { StateService } from "../state/state-service.js";
import type { MemoryService } from "../memory/memory-service.js";
import type { PolicyDecision } from "./types.js";

export class PolicyEngine {
  constructor(
    private readonly stopHandler: StopHandler,
    private readonly stateService: StateService,
    private readonly memoryService?: MemoryService
  ) {}

  /**
   * Evaluate whether a capability invocation is allowed.
   */
  async evaluate(
    spec: CapabilitySpec,
    params: Record<string, unknown>,
    context?: { role?: string; mode?: string; confirmed?: boolean }
  ): Promise<PolicyDecision> {
    const role = context?.role ?? "user";
    const mode = context?.mode ?? this.stateService.getMode();

    // 1. Emergency stop lock — blocks everything except READ_ONLY
    if (spec.risk_level !== "READ_ONLY" && this.stopHandler.isLocked()) {
      const remaining = this.stopHandler.remainingCooldownMs();
      return {
        allowed: false,
        code: ERROR_CODES.E_STATE_ESTOP,
        reason: `Emergency stop active, cooldown ${remaining}ms remaining`,
        userMessage: "Emergency stop is active. Please wait.",
        retryable: true,
        retryAfterMs: remaining,
      };
    }

    // 2. Mute mode check — deny capabilities with deny_when_muted=true
    if (mode === "mute" && spec.permissions.deny_when_muted) {
      return {
        allowed: false,
        code: ERROR_CODES.E_POLICY_ROLE_DENIED,
        reason: `Capability ${spec.capability_id} denied in mute mode`,
        userMessage: "This operation is not available in mute mode.",
        retryable: false,
      };
    }

    // 3. State predicates
    for (const predicate of spec.required_state_predicates) {
      const predicateResult = await this.checkPredicate(predicate);
      if (!predicateResult) {
        if (predicate.on_fail === "DENY") {
          return {
            allowed: false,
            code: `E_STATE_${predicate.key.toUpperCase()}`,
            reason: `State predicate failed: ${predicate.key} ${predicate.op} ${predicate.value}`,
            retryable: false,
          };
        }
        // on_fail === "CONFIRM" → need confirmation
        return {
          allowed: "confirm",
          reason: `State condition not met: ${predicate.key}`,
          confirmHint: `${predicate.key} check failed, proceed anyway?`,
        };
      }
    }

    // 4. Permission checks — roles
    if (!spec.permissions.roles_allowed.includes(role)) {
      return {
        allowed: false,
        code: ERROR_CODES.E_POLICY_ROLE_DENIED,
        reason: `Role '${role}' not allowed for ${spec.capability_id}`,
        retryable: false,
      };
    }

    // 5. Permission checks — modes
    if (spec.permissions.modes_allowed && !spec.permissions.modes_allowed.includes(mode)) {
      return {
        allowed: false,
        code: ERROR_CODES.E_POLICY_ROLE_DENIED,
        reason: `Mode '${mode}' not allowed for ${spec.capability_id}`,
        retryable: false,
      };
    }

    // 6. DANGEROUS capabilities — require confirmation
    if (spec.risk_level === "DANGEROUS" && spec.permissions.confirm_required) {
      if (!context?.confirmed) {
        return {
          allowed: "confirm",
          reason: `Dangerous capability ${spec.capability_id} requires confirmation`,
          confirmHint: spec.permissions.confirm_phrase_hint,
        };
      }
    }

    // 7. Device memory constraints — enforce speed limits from mode
    if (this.memoryService) {
      const constraintResult = this.applyDeviceConstraints(spec, params);
      if (constraintResult) return constraintResult;
    }

    return { allowed: true };
  }

  /**
   * Apply speed limits from current mode and device memory constraints.
   */
  private applyDeviceConstraints(
    spec: CapabilitySpec,
    params: Record<string, unknown>
  ): PolicyDecision | null {
    // Enforce speed limit for motion capabilities
    if (spec.capability_id.startsWith("tool.motion.") && params.speed !== undefined) {
      const maxSpeed = this.stateService.getMaxSpeed();
      if (typeof params.speed === "number" && params.speed > maxSpeed) {
        return {
          allowed: false,
          code: ERROR_CODES.E_POLICY_ROLE_DENIED,
          reason: `Speed ${params.speed} exceeds max ${maxSpeed} in ${this.stateService.getMode()} mode`,
          userMessage: `Speed limited to ${maxSpeed} in ${this.stateService.getMode()} mode.`,
          retryable: false,
        };
      }
    }

    // Check device memory constraints
    if (this.memoryService) {
      const constraints = this.memoryService.getDeviceConstraints();
      for (const constraint of constraints) {
        const content = constraint.content as Record<string, unknown>;
        if (content.capability_id === spec.capability_id && content.denied) {
          return {
            allowed: false,
            code: ERROR_CODES.E_POLICY_ROLE_DENIED,
            reason: `Device constraint: ${constraint.summary}`,
            userMessage: constraint.summary,
            retryable: false,
          };
        }
      }
    }

    return null;
  }

  // ─── Internal ─────────────────────────────────────────────

  private async checkPredicate(predicate: StatePredicate): Promise<boolean> {
    const stateValue = this.stateService.get(predicate.key);
    if (stateValue === undefined) return false;

    switch (predicate.op) {
      case "==":
        return stateValue === predicate.value;
      case "!=":
        return stateValue !== predicate.value;
      case ">":
        return (stateValue as number) > (predicate.value as number);
      case ">=":
        return (stateValue as number) >= (predicate.value as number);
      case "<":
        return (stateValue as number) < (predicate.value as number);
      case "<=":
        return (stateValue as number) <= (predicate.value as number);
      case "in":
        return Array.isArray(predicate.value) && predicate.value.includes(stateValue);
      default:
        return false;
    }
  }
}
