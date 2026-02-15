/**
 * SkillEngine — executes multi-step skill definitions.
 *
 * Features:
 * - Sequential step execution with condition checks
 * - Parameter resolution from previous step results ($ref syntax)
 * - Retry on error (configurable per step)
 * - Abort/skip on error
 * - Skill parameter substitution
 * - Cancellation support via AbortSignal
 */

import type { CapabilityExecutor, ExecutionResult } from "../capability/executor.js";
import type { PolicyEngine } from "../safety/policy-engine.js";
import type { CapabilityRegistry } from "../capability/registry.js";
import type { AuditLogger } from "../audit/audit-logger.js";
import type { StateService } from "../state/state-service.js";
import type { SkillDefinition, SkillStep, SkillExecutionResult, StepCondition } from "./types.js";
import { v4 as uuid } from "uuid";

export class SkillEngine {
  private readonly skills = new Map<string, SkillDefinition>();

  constructor(
    private readonly executor: CapabilityExecutor,
    private readonly policyEngine: PolicyEngine,
    private readonly registry: CapabilityRegistry,
    private readonly stateService: StateService,
    private readonly auditLogger: AuditLogger
  ) {}

  /**
   * Register a skill definition.
   */
  registerSkill(skill: SkillDefinition): void {
    this.skills.set(skill.skill_id, skill);
  }

  /**
   * Unregister a skill.
   */
  unregisterSkill(skillId: string): boolean {
    return this.skills.delete(skillId);
  }

  /**
   * Get all registered skill definitions.
   */
  listSkills(): SkillDefinition[] {
    return [...this.skills.values()];
  }

  /**
   * Get a skill by ID.
   */
  getSkill(skillId: string): SkillDefinition | undefined {
    return this.skills.get(skillId);
  }

  /**
   * Execute a skill with given parameters.
   */
  async execute(
    skillId: string,
    params: Record<string, unknown> = {},
    signal?: AbortSignal
  ): Promise<SkillExecutionResult> {
    const skill = this.skills.get(skillId);
    if (!skill) {
      return {
        skill_id: skillId,
        success: false,
        steps_completed: 0,
        steps_total: 0,
        results: {},
        error: `Skill not found: ${skillId}`,
      };
    }

    const traceId = uuid();
    this.auditLogger.info(traceId, "skill.start", {
      skill_id: skillId,
      params,
    });

    const stepResults: Record<string, unknown> = {};
    let stepsCompleted = 0;

    for (const step of skill.steps) {
      // Check for cancellation
      if (signal?.aborted) {
        this.auditLogger.info(traceId, "skill.cancelled", {
          skill_id: skillId,
          at_step: step.id,
        });
        return {
          skill_id: skillId,
          success: false,
          steps_completed: stepsCompleted,
          steps_total: skill.steps.length,
          results: stepResults,
          error: "Skill cancelled",
          aborted_at_step: step.id,
        };
      }

      // Check step condition
      if (step.condition && !this.evaluateCondition(step.condition, stepResults)) {
        this.auditLogger.info(traceId, "skill.step.skipped_condition", {
          step_id: step.id,
        });
        stepResults[step.id] = { skipped: true, reason: "condition_not_met" };
        stepsCompleted++;
        continue;
      }

      // Resolve parameters
      const resolvedParams = this.resolveParams(step, params, stepResults);

      // Optional delay
      if (step.delay_ms && step.delay_ms > 0) {
        await this.delay(step.delay_ms, signal);
      }

      // Execute with retries
      const maxRetries = step.on_error === "retry" ? (step.max_retries ?? 1) : 0;
      let lastError: string | undefined;
      let stepSuccess = false;

      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        // Policy check
        const cap = this.registry.getCapability(step.capability_id);
        if (cap) {
          const decision = await this.policyEngine.evaluate(cap.spec, resolvedParams);
          if (decision.allowed === false) {
            lastError = decision.reason;
            this.auditLogger.warn(traceId, "skill.step.denied", {
              step_id: step.id,
              reason: decision.reason,
            });
            break; // Policy denial is not retryable
          }
        }

        const result = await this.executor.execute(step.capability_id, resolvedParams);

        if (result.success) {
          stepResults[step.id] = result.data;
          stepSuccess = true;
          this.auditLogger.info(traceId, "skill.step.success", {
            step_id: step.id,
            attempt,
          });
          break;
        }

        lastError = result.error?.message ?? "Unknown error";
        this.auditLogger.warn(traceId, "skill.step.error", {
          step_id: step.id,
          attempt,
          error: lastError,
        });

        if (attempt < maxRetries) {
          await this.delay(500, signal); // Brief delay between retries
        }
      }

      if (!stepSuccess) {
        if (step.on_error === "skip") {
          stepResults[step.id] = { skipped: true, error: lastError };
          stepsCompleted++;
          continue;
        }

        // Default: abort
        this.auditLogger.error(traceId, "skill.abort", {
          skill_id: skillId,
          at_step: step.id,
          error: lastError,
        });
        return {
          skill_id: skillId,
          success: false,
          steps_completed: stepsCompleted,
          steps_total: skill.steps.length,
          results: stepResults,
          error: `Step ${step.id} failed: ${lastError}`,
          aborted_at_step: step.id,
        };
      }

      stepsCompleted++;
    }

    this.auditLogger.info(traceId, "skill.complete", {
      skill_id: skillId,
      steps_completed: stepsCompleted,
    });

    return {
      skill_id: skillId,
      success: true,
      steps_completed: stepsCompleted,
      steps_total: skill.steps.length,
      results: stepResults,
    };
  }

  /**
   * Evaluate a step condition.
   */
  private evaluateCondition(
    condition: StepCondition,
    stepResults: Record<string, unknown>
  ): boolean {
    if (condition.type === "state") {
      const snapshot = this.stateService.getSnapshot();
      const actual = (snapshot as Record<string, unknown>)[condition.key];
      return this.compareValues(actual, condition.op, condition.value);
    }

    if (condition.type === "previous_result") {
      const actual = this.resolvePath(stepResults, condition.path);
      if (condition.op === "truthy") return !!actual;
      if (condition.op === "falsy") return !actual;
      return this.compareValues(actual, condition.op, condition.value);
    }

    return true;
  }

  /**
   * Compare two values with given operator.
   */
  private compareValues(actual: unknown, op: string, expected: unknown): boolean {
    switch (op) {
      case "==": return actual === expected;
      case "!=": return actual !== expected;
      case ">": return (actual as number) > (expected as number);
      case "<": return (actual as number) < (expected as number);
      default: return false;
    }
  }

  /**
   * Resolve step params, substituting $ref values from previous results
   * and skill-level parameters.
   */
  private resolveParams(
    step: SkillStep,
    skillParams: Record<string, unknown>,
    stepResults: Record<string, unknown>
  ): Record<string, unknown> {
    const resolved = { ...step.params };

    // Substitute skill-level parameters (e.g., ${speed} → skillParams.speed)
    for (const [key, value] of Object.entries(resolved)) {
      if (typeof value === "string" && value.startsWith("${") && value.endsWith("}")) {
        const paramName = value.slice(2, -1);
        if (paramName in skillParams) {
          resolved[key] = skillParams[paramName];
        }
      }
    }

    // Substitute $ref values from previous step results
    if (step.param_refs) {
      for (const [key, refPath] of Object.entries(step.param_refs)) {
        resolved[key] = this.resolvePath(stepResults, refPath);
      }
    }

    return resolved;
  }

  /**
   * Resolve a dot-path (e.g., "step1.distance_cm") from an object.
   */
  private resolvePath(obj: Record<string, unknown>, path: string): unknown {
    const parts = path.split(".");
    let current: unknown = obj;
    for (const part of parts) {
      if (current == null || typeof current !== "object") return undefined;
      current = (current as Record<string, unknown>)[part];
    }
    return current;
  }

  /**
   * Delay helper that respects abort signal.
   */
  private delay(ms: number, signal?: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const timer = setTimeout(resolve, ms);
      signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
    });
  }
}
